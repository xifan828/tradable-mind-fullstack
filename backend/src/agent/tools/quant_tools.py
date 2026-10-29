"""Code execution for the quant agent: one persistent Python process per run.

`code_execution` runs the model's Python in a separate process that keeps its
namespace between calls, so a DataFrame downloaded on one call is still there on
the next one:

    df = download_market_data("EUR/USD", "4h")      # call 1
    df["gap"] = df["EMA20"] - df["EMA50"]           # call 2, same df

Nothing is written to disk. The session has no API keys and no network client of
its own: `download_market_data` inside the session sends an RPC line, and this
process — which already holds the credentials — does the fetch and hands the
DataFrame back pickled. Privilege stays on the trusted side of the pipe.

Lifecycle: a session is created on the first call of a run and keyed by
`QuantAgentContext.run_id`. `task` closes the run in its `finally`, which is the
only hook that also runs when the agent raises or the run is cancelled; a
`weakref.finalize` per session plus an `atexit` sweep cover the remaining paths
(server shutdown, dropped reference). Each session owns its process group and a
throwaway working directory, both destroyed on close.
"""

from __future__ import annotations

import asyncio
import atexit
import base64
import collections
import json
import logging
import os
import pickle
import queue
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import weakref
from pathlib import Path
from typing import Any

from langchain.tools import ToolRuntime, tool

from agent.prompts.technical_analysis import CODE_EXECUTION_DESCRIPTION
from agent.services.technical.technical_indicator import TechnicalIndicatorService
from agent.utils.twelve_data import AssetType

logger = logging.getLogger(__name__)

WORKER_PATH = Path(__file__).with_name("repl_worker.py")

# Wall-clock budget for a single submission. Analysing a whole 4000-bar series
# takes a couple of seconds; the limit exists to stop a runaway loop, not to rush
# legitimate work.
DEFAULT_TIMEOUT_SECONDS = 90.0

# The same idea one level down: a hard CPU and file-descriptor ceiling for the
# session, enforced by the kernel. The memory cap is enforced in this process by
# sampling the session's RSS: macOS rejects RLIMIT_AS for a forked child whose
# inherited address space is already larger than the requested limit, so the
# kernel cannot be trusted with this one on every platform.
MAX_CPU_SECONDS = 300
MAX_MEMORY_BYTES = 2 * 1024**3
MAX_OPEN_FILES = 256
MEMORY_SAMPLE_SECONDS = 1.0
MAX_OUTPUT_CHARS = 8000

# Shown on the call after the session was killed (timeout or memory budget), so
# the model knows why the variables it saw a moment ago are gone.
SHORT_RESTART_NOTE = (
    "Note: the session was killed, so it started empty — variables from earlier "
    "calls are gone; re-download the data if you need it."
)

# Sessions of a quant run, keyed by run id. At most one per concurrent quant
# task (OrchestratorContext.max_concurrent_tasks).
_SESSIONS: dict[str, ReplSession] = {}
_SESSIONS_LOCK = threading.Lock()


def _apply_process_limits() -> None:
    """Cap CPU, memory and descriptors of the session (runs in the child)."""
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, MAX_OPEN_FILES))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    except (ValueError, OSError):
        # Best effort: on macOS the forked child already maps more than the
        # ceiling, and the kernel refuses the limit. The parent samples RSS
        # instead (see ReplSession._memory_exceeded).
        pass


def _session_environment(workspace: str) -> dict[str, str]:
    """Build the environment of a session process.

    Deliberately minimal: the session needs no credentials, and no environment
    variable of the API server (API keys above all) may be readable from inside
    code the model wrote.
    """
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": workspace,
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "PYTHONUNBUFFERED": "1",
    }


def _kill_process_group(process: subprocess.Popen | None) -> None:
    """SIGKILL the session's whole process group and reap it."""
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    try:
        # Without the wait the killed child stays a zombie until the server exits.
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover - unkillable process
        logger.warning("Code execution session %s did not exit after SIGKILL", process.pid)


def _release(process: subprocess.Popen | None, workspace: str | None) -> None:
    """Backstop cleanup for a session that was never closed explicitly."""
    _kill_process_group(process)
    if workspace:
        shutil.rmtree(workspace, ignore_errors=True)


class ReplSession:
    """A Python process that keeps the agent's variables between calls."""

    def __init__(self, asset_type: AssetType | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        """Create a session (the process starts on the first call).

        Args:
            asset_type: Asset class of the run, used when fetching market data.
            timeout: Wall-clock limit for a single submission, in seconds.
        """
        self.asset_type = asset_type
        self.timeout = timeout
        self.privileged_calls = 0
        self._process: subprocess.Popen | None = None
        self._workspace: str | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._stderr_tail: collections.deque[str] = collections.deque(maxlen=40)
        self._lock = threading.Lock()
        self._finalizer: weakref.finalize | None = None
        # Set once a process has been started, so the first call of a run is not
        # told that "earlier calls" lost their variables.
        self._spawned = False
        # Message handed to the next call after the session was killed or died.
        self._dead_process_note: str | None = None

    # ---------------------------------------------------------------- process

    def _is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        """Start a fresh session process with an empty namespace."""
        self._workspace = tempfile.mkdtemp(prefix="quant-code-execution-")
        self._spawned = True
        self._process = subprocess.Popen(
            [sys.executable, "-u", str(WORKER_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._workspace,
            env=_session_environment(self._workspace),
            start_new_session=True,
            preexec_fn=_apply_process_limits,
        )
        self._lines = queue.Queue()
        self._finalizer = weakref.finalize(self, _release, self._process, self._workspace)
        for stream, is_protocol in ((self._process.stdout, True), (self._process.stderr, False)):
            threading.Thread(target=self._pump, args=(stream, is_protocol), daemon=True).start()

    def _pump(self, stream: Any, is_protocol: bool) -> None:
        """Feed protocol lines to the queue, keep a tail of the session's stderr."""
        for line in iter(stream.readline, ""):
            if is_protocol:
                self._lines.put(line)
            else:
                self._stderr_tail.append(line.rstrip())
        self._lines.put(None)

    def stop(self) -> None:
        """Kill the session and remove its working directory."""
        if self._finalizer is not None:
            self._finalizer()
            self._finalizer = None
        else:
            _release(self._process, self._workspace)
        self._process = None
        self._workspace = None

    # ---------------------------------------------------------------- execution

    def execute(self, code: str) -> str:
        """Run one submission and return what the model should read."""
        with self._lock:
            note = self._dead_process_note
            self._dead_process_note = None
            if not self._is_alive():
                restart_of_dead_session = self._spawned
                self.stop()
                self.start()
                if note is None and restart_of_dead_session:
                    note = (
                        "Note: this session had ended before the call, so it started empty. "
                        "Variables from earlier calls are gone — re-download the data if you need it."
                    )

            assert self._process is not None and self._process.stdin is not None
            started = time.perf_counter()
            try:
                self._process.stdin.write(json.dumps({"code": code}) + "\n")
                self._process.stdin.flush()
            except (BrokenPipeError, OSError):
                self.stop()
                return f"Error: the code session died before running the code ({self._death_reason()})."

            result = self._collect(time.monotonic() + self.timeout)
            elapsed = time.perf_counter() - started

            if result is None:
                self.stop()
                logger.warning("Code execution session timed out after %.0fs", self.timeout)
                self._dead_process_note = SHORT_RESTART_NOTE
                return (
                    f"Error: the code did not finish within {self.timeout:.0f}s and the session was "
                    "killed. It starts empty next, so variables from earlier calls are gone. "
                    "Re-download the data and work in smaller steps."
                )

            if result.get("status") == "memory":
                self.stop()
                logger.warning("Code execution session exceeded its memory budget")
                self._dead_process_note = SHORT_RESTART_NOTE
                return (
                    f"Error: the code used more than {MAX_MEMORY_BYTES / 1024**3:.1f} GB and the session "
                    "was killed. It starts empty next, so variables from earlier calls are gone. "
                    "Work on a smaller slice of the data."
                )

            prefix = f"{note}\n\n" if note else ""
            return prefix + self._format(result, elapsed)

    def _death_reason(self) -> str:
        tail = " | ".join(list(self._stderr_tail)[-3:])
        return tail or "the process exited unexpectedly."

    def _collect(self, deadline: float) -> dict[str, Any] | None:
        """Wait for this submission's result line, servicing parent-side RPC calls.

        A submission that allocates without bound is stopped from here: the
        kernel limit is only reliable on Linux, so the parent samples the
        session's resident memory while it works.
        """
        next_memory_check = time.monotonic() + MEMORY_SAMPLE_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                line = self._lines.get(timeout=min(remaining, 0.25))
            except queue.Empty:
                if time.monotonic() >= next_memory_check:
                    next_memory_check = time.monotonic() + MEMORY_SAMPLE_SECONDS
                    if self._memory_exceeded():
                        return {"status": "memory", "stdout": "", "stderr": "", "variables": {}}
                continue
            if line is None:
                return None
            if not line.startswith("{"):
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("op") == "rpc":
                self.privileged_calls += 1
                self._reply(self._privileged(message))
                continue
            if message.get("op") == "result":
                return message
            # "ready" and anything else: keep waiting for the result.

    def _memory_exceeded(self) -> bool:
        """Whether the session process is over its memory budget."""
        if self._process is None or self._process.poll() is not None:
            return False
        try:
            listing = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(self._process.pid)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            resident_bytes = int(listing.stdout.strip() or 0) * 1024
        except (ValueError, OSError, subprocess.SubprocessError):
            return False
        return resident_bytes > MAX_MEMORY_BYTES

    def _reply(self, payload: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            return
        try:
            self._process.stdin.write(json.dumps(payload) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            logger.warning("Code execution session closed while answering an RPC call")

    # ---------------------------------------------------------------- privilege

    def _privileged(self, message: dict[str, Any]) -> dict[str, Any]:
        """Run a request from the session in this (trusted) process."""
        call = message.get("call")
        kwargs = dict(message.get("kwargs") or {})
        try:
            if call == "download_market_data":
                frame = self.fetch_market_data(**kwargs)
                return {"pickle": True, "data": base64.b64encode(pickle.dumps(frame)).decode()}
            return {"error": f"Unknown session request '{call}'."}
        except Exception as exc:  # handed to the model as the call's error text
            return {"error": f"{type(exc).__name__}: {exc}"}

    def fetch_market_data(
        self,
        ticker: str,
        interval: str,
        data_provider: str = "twelvedata",
        timezone: str = "UTC",
        outputsize: int = 4000,
    ):
        """Fetch OHLC bars with pre-calculated indicators for the session.

        Args:
            ticker: Asset symbol, e.g. "EUR/USD", "BTC/USD", "AAPL", "DX-Y.NYB".
            interval: Bar size, e.g. "15min", "1h", "4h", "1day".
            data_provider: "twelvedata" (forex, crypto, stocks, commodities) or
                "yfinance" (indices, treasury yields).
            timezone: Timezone the bars are returned in.
            outputsize: Number of bars requested (max 5000).

        Returns:
            The DataFrame the session will hold in memory.

        Raises:
            ValueError: The provider returned no data (wrong symbol or interval).
        """
        service = TechnicalIndicatorService(
            symbol=ticker,
            timezone=timezone,
            interval=interval,
            asset_type=self.asset_type,
        )
        if data_provider == "yfinance":
            frame = service.get_data_from_yfinance(outputsize=outputsize)
        else:
            frame = service.get_data_from_td(outputsize=outputsize)

        if frame is None or frame.empty:
            raise ValueError(f"No data returned for {ticker} at {interval}. Check the symbol.")
        return frame

    # ---------------------------------------------------------------- formatting

    @staticmethod
    def _format(result: dict[str, Any], elapsed: float) -> str:
        """Render a submission's result for the model."""
        parts: list[str] = []
        if result.get("stdout", "").strip():
            parts.append(result["stdout"].rstrip())
        if result.get("stderr", "").strip():
            parts.append(result["stderr"].rstrip())
        if result.get("status") == "blocked":
            parts.append("The code was not executed.")
        elif not parts:
            parts.append("Executed with no output.")
        if result.get("variables"):
            parts.append(
                "Variables in memory: "
                + ", ".join(f"{name} ({kind})" for name, kind in result["variables"].items())
            )
        body = "\n".join(parts)
        if len(body) > MAX_OUTPUT_CHARS:
            body = body[:MAX_OUTPUT_CHARS] + "\n... (output truncated)"
        return f"{body}\n\n({elapsed:.2f}s)"


# ------------------------------------------------------------------ registry


def _session_key(context: Any) -> str:
    """Registry key of the session belonging to this agent run."""
    run_id = getattr(context, "run_id", None)
    # Without a run id (a hand-built context in a script or a test) the context
    # object itself identifies the run; it lives as long as the run does.
    return run_id or f"context-{id(context)}"


def _session_for(context: Any) -> ReplSession:
    """Return the code session of this run, creating it on first use."""
    key = _session_key(context)
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(key)
        if session is None:
            session = ReplSession(asset_type=getattr(context, "asset_type", None))
            _SESSIONS[key] = session
        return session


def _pop_session(run_id: str | None) -> ReplSession | None:
    """Take the run's session out of the registry, if it has one."""
    if not run_id:
        return None
    with _SESSIONS_LOCK:
        return _SESSIONS.pop(run_id, None)


def close_run(run_id: str | None) -> None:
    """Close the code session of a finished quant run.

    Called from the `task` tool's `finally`, so it also runs when the agent
    raised or the run was cancelled — an `after_agent` hook inside the graph does
    not fire on those paths. Async callers use `aclose_run` instead.
    """
    session = _pop_session(run_id)
    if session is not None:
        session.stop()


async def aclose_run(run_id: str | None) -> None:
    """`close_run` for a coroutine, without stalling the event loop.

    `ReplSession.stop` SIGKILLs the session's process group and then *waits* for
    the kernel to reap it (`subprocess.wait`, i.e. a `time.sleep` poll). Under an
    ASGI server that wait runs on the event loop and holds up every other run —
    langgraph dev rejects it outright as a blocking call — so the teardown is
    handed to a worker thread. The session is popped from the registry first, so
    the run cannot be reused while its process is being torn down.
    """
    session = _pop_session(run_id)
    if session is not None:
        await asyncio.to_thread(session.stop)


def close_all_sessions() -> None:
    """Close every open session (server-shutdown backstop)."""
    with _SESSIONS_LOCK:
        sessions = list(_SESSIONS.values())
        _SESSIONS.clear()
    for session in sessions:
        session.stop()


atexit.register(close_all_sessions)


# ------------------------------------------------------------------ the tool


@tool(description=CODE_EXECUTION_DESCRIPTION, parse_docstring=True)
def code_execution(code: str, runtime: ToolRuntime) -> str:
    """Execute Python code in a session that keeps its variables between calls.

    Args:
        code: Python code to run. Use print(), or leave the value you want to see
            as the last expression of the code.

    Returns:
        Everything the code printed, its traceback if it failed, and the
        variables that are now held in memory.
    """
    if not code or not code.strip():
        return "Error: no code provided."
    return _session_for(runtime.context).execute(code)
