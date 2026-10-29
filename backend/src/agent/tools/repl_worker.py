"""Sandboxed Python REPL worker: one process per quantitative analysis run.

Started by `agent.tools.quant_tools` as `python -u <this file>` with a scrubbed
environment, its own process group and resource limits. It keeps a single
namespace for the whole session, so a variable defined by one `code_execution`
call is still there on the next call — the agent measures in memory instead of
round-tripping through CSV files.

Protocol, one JSON object per line in each direction:

    parent -> worker  {"code": "..."} | {"op": "shutdown"}
    worker -> parent  {"op": "ready", "python": "3.12.15"}
    worker -> parent  {"op": "result", "status": "ok|error|blocked", ...}
    worker -> parent  {"op": "rpc", "call": "download_market_data", "kwargs": {...}}
    parent -> worker  {"pickle": true, "data": "<base64>"} | {"error": "..."}

The protocol travels on a private duplicate of stdout, so code under execution
can use stdout/stderr normally; both are captured per call and returned with a
summary of the variables that are now in memory.

Privileged work never happens here. `download_market_data` writes an RPC line
and blocks until the parent answers with a pickled DataFrame: the network call
and the API key stay in the trusted process, and the data lands directly in this
namespace. Nothing is written to disk.

What this module is not: a security boundary on its own. `_blocked_reason`
rejects the obvious accidents (imports outside the allowlist, dunder access,
shell/process attributes), but a determined string can walk around a source
check. The boundary is the separate process, its resource limits and its
environment — see `quant_tools.ReplSession`.
"""

from __future__ import annotations

import ast
import base64
import io
import json
import os
import pickle
import sys
import traceback
from typing import Any, cast

_PROTOCOL = os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1)

MAX_STDOUT_CHARS = 6000
MAX_STDERR_CHARS = 4000

# Imports the analysis code may use. Everything else is rejected before it runs:
# the worker needs no filesystem, no subprocess and no network of its own.
ALLOWED_IMPORTS = frozenset(
    {
        "collections",
        "datetime",
        "decimal",
        "functools",
        "itertools",
        "json",
        "math",
        "numpy",
        "pandas",
        "random",
        "re",
        "statistics",
        "talib",
        "time",
        "typing",
    }
)

# Names and attribute names that have no place in a market-data calculation.
BLOCKED_NAMES = frozenset(
    {
        "__builtins__",
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "exit",
        "globals",
        "input",
        "locals",
        "open",
        "quit",
        "vars",
    }
)

BLOCKED_ATTRIBUTES = frozenset(
    {
        "__bases__",
        "__builtins__",
        "__class__",
        "__code__",
        "__globals__",
        "__mro__",
        "__subclasses__",
        "chdir",
        "connect",
        "environ",
        "execv",
        "execve",
        "fork",
        "getcwd",
        "kill",
        "killpg",
        "listdir",
        "makedirs",
        "mkdir",
        "popen",
        "putenv",
        "remove",
        "removedirs",
        "rename",
        "rmdir",
        "rmtree",
        "spawn",
        "spawnl",
        "socket",
        "system",
        "unlink",
        "urlopen",
        "walk",
        "write_bytes",
    }
)


def _send(payload: dict[str, Any]) -> None:
    """Write one protocol line to the parent."""
    _PROTOCOL.write(json.dumps(payload) + "\n")


def _rpc(call: str, **kwargs: Any) -> Any:
    """Ask the parent process to run a privileged operation for us."""
    _send({"op": "rpc", "call": call, "kwargs": kwargs})
    line = sys.stdin.readline()
    if not line:
        raise RuntimeError("The analysis session was closed before the request finished.")
    reply = json.loads(line)
    if "error" in reply:
        raise RuntimeError(reply["error"])
    if reply.get("pickle"):
        return pickle.loads(base64.b64decode(reply["data"]))
    return reply.get("data")


def download_market_data(
    ticker: str,
    interval: str,
    data_provider: str = "twelvedata",
    timezone: str = "UTC",
    outputsize: int = 4000,
):
    """Return OHLC data with pre-calculated indicators as a pandas DataFrame.

    Args:
        ticker: Asset symbol, e.g. "EUR/USD", "BTC/USD", "AAPL", "DX-Y.NYB".
        interval: Bar size, e.g. "1min", "15min", "1h", "4h", "1day", "1week".
        data_provider: "twelvedata" (forex, crypto, stocks, commodities) or
            "yfinance" (indices, treasury yields).
        timezone: Exchange timezone for the bars, e.g. "UTC".
        outputsize: Number of bars to fetch (max 5000).

    Returns:
        DataFrame with Date, Open, High, Low, Close and the indicator columns
        (EMA10/EMA20/EMA50/EMA100, BB_Upper/BB_Middle/BB_Lower, MACD,
        MACD_Signal, MACD_Diff, RSI14, ATR, ROC12). It stays in this session's
        memory until the run ends.
    """
    return _rpc(
        "download_market_data",
        ticker=ticker,
        interval=interval,
        data_provider=data_provider,
        timezone=timezone,
        outputsize=outputsize,
    )


def _blocked_reason(code: str) -> str | None:
    """Return why the code is refused, or None when it passes the guardrail."""
    try:
        tree = ast.parse(code, "<code>", "exec")
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    return f"import of '{alias.name}' is not allowed"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                return f"import from '{node.module}' is not allowed"
        elif isinstance(node, ast.Attribute):
            if node.attr in BLOCKED_ATTRIBUTES or node.attr.startswith("__"):
                return f"attribute access '{node.attr}' is not allowed"
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_NAMES:
                return f"use of '{node.id}' is not allowed"
    return None


def _run_source(code: str, namespace: dict[str, Any]) -> None:
    """Execute code, echoing the value of a trailing expression like a REPL."""
    tree = ast.parse(code, "<code>", "exec")
    trailing: ast.Expression | None = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        expression = cast(ast.Expr, tree.body.pop())
        trailing = ast.Expression(expression.value)
        ast.fix_missing_locations(trailing)

    if tree.body:
        exec(compile(tree, "<code>", "exec"), namespace)

    if trailing is not None:
        value = eval(compile(trailing, "<code>", "eval"), namespace)
        if value is not None:
            sys.displayhook(value)


def _summarize(namespace: dict[str, Any]) -> dict[str, str]:
    """Describe the variables left in the namespace by name."""
    summary: dict[str, str] = {}
    for name, value in namespace.items():
        if name.startswith("_"):
            continue
        kind = type(value).__name__
        if kind in ("module", "function", "builtin_function_or_method", "type"):
            continue
        shape = getattr(value, "shape", None)
        if shape is not None:
            summary[name] = f"{kind}{tuple(shape)}"
        elif kind in ("int", "float", "str", "bool", "Timestamp"):
            summary[name] = f"{kind} = {repr(value)[:60]}"
        else:
            summary[name] = kind
    return summary


def _build_namespace() -> dict[str, Any]:
    """Preload the analysis stack so the first call needs no import lines."""
    import math

    import numpy as np
    import pandas as pd
    import talib

    return {
        "__name__": "__code_execution__",
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "math": math,
        "talib": talib,
        "download_market_data": download_market_data,
    }


def _execute(code: str, namespace: dict[str, Any]) -> dict[str, Any]:
    """Run one submission and collect what the model should see."""
    reason = _blocked_reason(code)
    if reason is not None:
        return {"status": "blocked", "stdout": "", "stderr": f"Blocked: {reason}.",
                "variables": _summarize(namespace)}

    stdout, stderr = io.StringIO(), io.StringIO()
    saved = (sys.stdout, sys.stderr, sys.displayhook)
    sys.stdout, sys.stderr = stdout, stderr
    sys.displayhook = lambda value: stdout.write(repr(value) + "\n")
    status = "ok"
    try:
        _run_source(code, namespace)
    except SystemExit:
        status = "error"
        stderr.write("SystemExit: exiting the session is not allowed.\n")
    except BaseException:
        status = "error"
        traceback.print_exc(file=stderr)
    finally:
        sys.stdout, sys.stderr, sys.displayhook = saved

    return {
        "status": status,
        "stdout": stdout.getvalue()[-MAX_STDOUT_CHARS:],
        "stderr": stderr.getvalue()[-MAX_STDERR_CHARS:],
        "variables": _summarize(namespace),
    }


def main() -> None:
    """Serve code submissions until the parent closes the session."""
    namespace = _build_namespace()
    _send({"op": "ready", "python": sys.version.split()[0]})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if request.get("op") == "shutdown":
            break
        code = request.get("code", "")
        try:
            result = _execute(code, namespace)
        except BaseException:  # pragma: no cover - _execute catches its own errors
            result = {"status": "error", "stdout": "", "stderr": traceback.format_exc(),
                      "variables": _summarize(namespace)}
        _send({"op": "result", **result})


if __name__ == "__main__":
    main()
