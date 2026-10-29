"""The quant agent's code execution session.

These exercise the real worker process: variables surviving between calls,
guardrails, the parent-side data RPC, the timeout, and the teardown contract.
Network access is not needed — the data provider is stubbed.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pandas as pd
import pytest
from blockbuster import blockbuster_ctx

from agent.states_and_contexts.technical_analysis import QuantAgentContext
from agent.tools.quant_tools import (
    _SESSIONS,
    ReplSession,
    aclose_run,
    close_run,
    code_execution,
)


@pytest.fixture
def session():
    session = ReplSession(asset_type="forex", timeout=20.0)
    yield session
    session.stop()


def _alive(session: ReplSession) -> bool:
    assert session._process is not None
    return session._process.poll() is None


def test_tool_takes_only_code():
    """The model sees a single `code` argument, nothing else."""
    assert sorted(code_execution.tool_call_schema.model_json_schema()["properties"]) == ["code"]


def test_first_call_carries_no_restart_note(session):
    """The first call of a run must not claim that earlier variables are gone."""
    out = session.execute("1 + 1")

    assert "earlier calls" not in out
    assert "started empty" not in out


def test_variables_survive_between_calls(session):
    session.execute("df = pd.DataFrame({'Close': [1.0, 2.0, 3.0]})")
    out = session.execute("df['Close'].sum()")

    assert "6.0" in out
    assert "df (DataFrame(3, 1))" in out


def test_last_expression_is_echoed_like_a_repl(session):
    assert "4" in session.execute("2 + 2")


def test_error_does_not_end_the_session(session):
    session.execute("xs = [1, 2, 3]")
    out = session.execute("1 / 0")

    assert "ZeroDivisionError" in out
    assert "xs (list)" in session.execute("len(xs)")


def test_pandas_numpy_talib_are_preloaded(session):
    out = session.execute("talib.SMA(np.array([1.0, 2.0, 3.0, 4.0]), timeperiod=2)")

    assert "nan" in out


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "import subprocess",
        "from shutil import rmtree",
        "__import__('os')",
        "open('/etc/hosts')",
        "eval('1 + 1')",
        "pd.io.common.os.system('id')",
    ],
)
def test_guardrail_blocks_escapes(session, code):
    out = session.execute(code)

    assert "not allowed" in out
    assert "The code was not executed." in out


def test_market_data_rpc_hands_a_dataframe_into_the_session(session, monkeypatch):
    """download_market_data runs in the parent and the frame lands in memory."""
    frame = pd.DataFrame({"Close": [1.0, 1.5, 2.0], "RSI14": [50.0, 55.0, 60.0]})
    monkeypatch.setattr(
        ReplSession, "fetch_market_data", lambda self, **kwargs: frame
    )

    out = session.execute('df = download_market_data("EUR/USD", "4h", outputsize=3)\ndf.shape')

    assert "(3, 2)" in out
    assert session.privileged_calls == 1
    assert "df (DataFrame(3, 2))" in session.execute("df.describe()")


def test_fetch_errors_reach_the_model(monkeypatch):
    session = ReplSession(asset_type="forex", timeout=20.0)
    monkeypatch.setattr(
        ReplSession,
        "fetch_market_data",
        lambda self, **kwargs: (_ for _ in ()).throw(ValueError("No data returned for NOPE.")),
    )
    try:
        out = session.execute('download_market_data("NOPE", "4h")')
    finally:
        session.stop()

    assert "ValueError: No data returned for NOPE." in out
    assert session._process is None


def test_runaway_code_is_killed_and_the_session_restarts_empty():
    session = ReplSession(asset_type="forex", timeout=3.0)
    try:
        session.execute("kept = 1")
        started = time.perf_counter()
        out = session.execute("while True:\n    pass")
        elapsed = time.perf_counter() - started

        assert "did not finish within 3s" in out
        assert 3.0 <= elapsed < 15.0
        assert session._process is None  # killed and forgotten, not left running

        # The next call works, in a fresh namespace, and says so.
        follow_up = session.execute("'kept' in dir()")
        assert "started empty" in follow_up
        assert "False" in follow_up
    finally:
        session.stop()


def test_close_run_kills_the_session_and_forgets_it():
    context = QuantAgentContext(asset_type="forex", run_id="run-under-test")
    runtime = SimpleNamespace(context=context)

    assert code_execution.func(code="df = pd.DataFrame({'a': [1]})", runtime=runtime)
    session = _SESSIONS["run-under-test"]
    assert _alive(session) is True
    pid = session._process.pid

    close_run("run-under-test")

    assert "run-under-test" not in _SESSIONS
    # No zombie either: the process is gone as far as the OS is concerned.
    with pytest.raises(OSError):
        import os

        os.kill(pid, 0)


def test_async_close_does_not_block_the_event_loop():
    """The async teardown must not sleep on the loop, as langgraph dev enforces.

    Closing a session SIGKILLs its process group and then *waits* for the kernel
    to reap it — `subprocess.wait`, i.e. a polling `time.sleep`. Called straight
    from a coroutine (as the `task` tool's `finally` would) that wait runs on the
    event loop and every other run stalls behind it, so `aclose_run` moves the
    whole teardown to a worker thread.
    """
    context = QuantAgentContext(asset_type="forex", run_id="run-async-under-test")
    runtime = SimpleNamespace(context=context)
    assert code_execution.func(code="kept = 1", runtime=runtime)
    pid = _SESSIONS["run-async-under-test"]._process.pid

    async def close() -> None:
        with blockbuster_ctx():
            await aclose_run("run-async-under-test")

    asyncio.run(close())

    assert "run-async-under-test" not in _SESSIONS
    # Reaped, not just killed: the pid is gone as far as the OS is concerned.
    with pytest.raises(OSError):
        import os

        os.kill(pid, 0)


def test_sessions_are_isolated_per_run():
    runtimes = [
        SimpleNamespace(context=QuantAgentContext(asset_type="forex", run_id=run_id))
        for run_id in ("run-a", "run-b")
    ]
    try:
        for runtime, value in zip(runtimes, ("1", "2"), strict=True):
            code_execution.func(code=f"marker = {value}", runtime=runtime)

        for runtime, value in zip(runtimes, ("1", "2"), strict=True):
            out = code_execution.func(code="marker", runtime=runtime)
            assert value in out
    finally:
        close_run("run-a")
        close_run("run-b")


def test_parallel_runs_get_their_own_process():
    """Four concurrent runs (max_concurrent_tasks) keep four separate namespaces."""
    sessions = [ReplSession(asset_type="forex", timeout=30.0) for _ in range(4)]
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(session.execute, f"value = {index}\nvalue * 10")
                for index, session in enumerate(sessions)
            ]
            outputs = [future.result() for future in futures]

        for index, output in enumerate(outputs):
            assert f"{index * 10}" in output
        assert len({session._process.pid for session in sessions}) == 4
    finally:
        for session in sessions:
            session.stop()


def test_two_calls_in_one_turn_share_the_session_without_corrupting_it():
    """A model may emit two calls at once; they are serialised on one namespace."""
    session = ReplSession(asset_type="forex", timeout=30.0)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(session.execute, "x = 1\nx")
            second = pool.submit(session.execute, "y = 2\ny")

        assert "1" in first.result()
        assert "2" in second.result()
        # Both survived: the two results were not mixed up with each other.
        combined = session.execute("x + y")
        assert "3" in combined
        assert "x (int" in combined and "y (int" in combined
    finally:
        session.stop()
