from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
import talib
import math
import io
import sys
import traceback
import os
import asyncio
import atexit

from agent.services.technical.technical_indicator import TechnicalIndicatorService
from agent.config.settings import BASE_DIR
from agent.prompts.technical_analysis import (DOWNLOAD_MARKET_DATA_DESCRIPTION,
                                            WRITE_CODE_DESCRIPTION
                                            )

# Default data directory (used as fallback if no session directory)
DEFAULT_DATA_DIR = BASE_DIR / "data" / "time_series"

@tool(description=DOWNLOAD_MARKET_DATA_DESCRIPTION, parse_docstring=True)
def download_market_data(
    ticker: str,
    interval: str,
    runtime: ToolRuntime,
    data_provider: str = "twelvedata",
    timezone: str = "UTC",
    outputsize: int = 4000,
) -> Command | str:
    """Download OHLC market data with pre-calculated technical indicators for a given asset.

    Args:
        ticker: Asset ticker symbol (e.g., "EUR/USD", "BTC/USD", "XAU/USD", "GBP/USD" for TwelveData; "DX-Y.NYB", "^TNX" for yfinance)
        interval: Time interval for the data (e.g., "1min", "5min", "15min", "30min", "1h", "4h", "1day", "1week")
        data_provider: Data source - "twelvedata" (default) for forex/crypto/stocks/commodities, "yfinance" for indices/treasury yields
        timezone: Timezone for the data (default: "UTC"). Examples: "America/New_York", "Europe/London"
        outputsize: Number of data points to fetch (default: 4000, max: 5000)

    Returns:
        Message with saved file path and preview of first 5 rows
    """

    try:
        # Get asset_type from context if available
        asset_type = runtime.context.asset_type if hasattr(runtime.context, 'asset_type') else None

        service = TechnicalIndicatorService(
            symbol=ticker,
            timezone=timezone,
            interval=interval,
            asset_type=asset_type
        )

        if data_provider == "yfinance":
            df = service.get_data_from_yfinance(outputsize=outputsize)
        else:
            df = service.get_data_from_td(outputsize=outputsize)

        if df is None or df.empty:
            return f"Error: No data returned for {ticker} at {interval} interval."

        # Use session-specific directory if available, otherwise default
        data_dir = Path(runtime.context.session_data_dir) if runtime.context.session_data_dir else DEFAULT_DATA_DIR
        data_dir.mkdir(parents=True, exist_ok=True)

        ticker_clean = ticker.replace("/", "_")
        filename = f"{ticker_clean}_{interval}.csv"
        filepath = data_dir / filename

        df.to_csv(filepath, index=True)

        preview = df.head(5).to_string()

        # Just return the new file - operator.add reducer will merge with existing list
        new_files = [str(filepath)]

        result_message = f"""Successfully downloaded {len(df)} rows of data for {ticker} ({interval}).

File saved to: {filepath}

Available columns: {', '.join(df.columns.tolist())}

First 5 rows:
{preview}

You can now use the write_code tool to analyze this data. Load it with:
df = read_csv("{filename}")

The Date column is automatically parsed as datetime, so you can do date filtering like:
df[df['Date'] >= df['Date'].max() - pd.Timedelta(days=30)]
"""

        return Command(
            update={
                "downloaded_files": new_files,
                "messages": [
                    ToolMessage(
                        content=result_message,
                        tool_call_id=runtime.tool_call_id
                    )
                ]
            }
        )

    except Exception as e:
        return f"Error downloading data for {ticker}: {str(e)}. Fix it, the error most likely is due to an invalid ticker symbol."
    
_code_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the thread pool executor."""
    global _code_executor
    if _code_executor is None:
        _code_executor = ThreadPoolExecutor(max_workers=4)
        atexit.register(_shutdown_executor)
    return _code_executor


def _shutdown_executor():
    """Shutdown the executor on exit."""
    global _code_executor
    if _code_executor is not None:
        _code_executor.shutdown(wait=True)
        _code_executor = None

BLOCKED_BUILTINS = {
    'eval',
    'exec',
    'compile',
    'open',
    'input',
    'breakpoint',
}

DANGEROUS_PATTERNS = [
    'os.system',
    'os.popen',
    'os.spawn',
    'os.exec',
    'subprocess',
    'shutil.rmtree',
    'shutil.move',
    '__import__',
    'importlib',
    'pickle',
    'socket',
    'requests.',
    'urllib',
    'http.client',
    'ftplib',
    'telnetlib',
    'smtplib',
]


def _create_safe_open(allowed_dir: Path):
    """Create a safe open function that only allows reading from allowed directory."""
    def safe_open(filepath: str, mode: str = 'r', *args, **kwargs):
        if 'w' in mode or 'a' in mode or 'x' in mode or '+' in mode:
            raise PermissionError("Write operations are not allowed. Only reading is permitted.")

        resolved_path = Path(filepath).resolve()
        allowed_resolved = allowed_dir.resolve()

        try:
            resolved_path.relative_to(allowed_resolved)
        except ValueError:
            raise PermissionError(
                f"Access denied. Only files in {allowed_dir} can be read. "
                f"Attempted to access: {filepath}"
            )

        if not str(resolved_path).endswith('.csv'):
            raise PermissionError("Only .csv files can be read.")

        return open(resolved_path, mode, *args, **kwargs)

    return safe_open


def _create_safe_builtins():
    """Create a restricted builtins dictionary."""
    import builtins
    safe_builtins = {}

    for name in dir(builtins):
        if name not in BLOCKED_BUILTINS and not name.startswith('_'):
            safe_builtins[name] = getattr(builtins, name)

    safe_builtins['True'] = True
    safe_builtins['False'] = False
    safe_builtins['None'] = None

    # __import__ is needed by numpy/pandas/talib for internal operations
    # Security is enforced via DANGEROUS_PATTERNS check before execution
    safe_builtins['__import__'] = builtins.__import__

    return safe_builtins


def _execute_sandboxed_code(code: str, data_dir: Path) -> str:
    """Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute
        data_dir: Directory where data files are stored (session-specific)
    """

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    try:
        safe_globals = {
            '__builtins__': _create_safe_builtins(),
            '__name__': '__sandbox__',
        }

        safe_globals['pd'] = pd
        safe_globals['pandas'] = pd
        safe_globals['np'] = np
        safe_globals['numpy'] = np
        safe_globals['math'] = math
        safe_globals['talib'] = talib

        safe_globals['open'] = _create_safe_open(data_dir)

        def safe_read_csv(filepath, **kwargs):
            """Read CSV file from the session data directory.

            Automatically parses the Date column as datetime and sets it as index.
            """
            resolved = Path(filepath)
            if not resolved.is_absolute():
                resolved = data_dir / filepath

            try:
                resolved.resolve().relative_to(data_dir.resolve())
            except ValueError:
                raise PermissionError(f"Access denied. Only files in {data_dir} can be read.")

            # Set smart defaults for market data CSVs
            # Use first column as index (which is numeric), but also parse Date column
            if 'index_col' not in kwargs:
                kwargs['index_col'] = 0

            df = pd.read_csv(resolved, **kwargs)

            # Auto-convert Date column to datetime if it exists
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])

            return df

        safe_globals['read_csv'] = safe_read_csv
        safe_globals['DATA_DIR'] = str(data_dir)

        safe_locals = {}

        exec(code, safe_globals, safe_locals)

        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        output = ""
        if stdout_output:
            output += stdout_output
        if stderr_output:
            output += f"\nStderr:\n{stderr_output}"

        if not output.strip():
            output = "Code executed successfully (no output)."

        return output

    except Exception as e:
        error_msg = f"Error executing code:\n{traceback.format_exc()}"
        return error_msg

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

@tool(description=WRITE_CODE_DESCRIPTION, parse_docstring=True)
async def write_code(
    code: str,
    runtime: ToolRuntime,
) -> str:
    """Execute Python code for quantitative analysis in a sandboxed environment.

    Args:
        code: Python code string to execute. Use print() to output results.

    Returns:
        The printed output from the code execution, or error message if failed.
    """
    if not code or not code.strip():
        return "Error: No code provided."

    code_lower = code.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in code_lower:
            return f"Error: Blocked pattern detected: '{pattern}'. This operation is not allowed for security reasons."

    # Use session-specific directory if available, otherwise default
    data_dir = Path(runtime.context.session_data_dir) if runtime.context.session_data_dir else DEFAULT_DATA_DIR

    # Run code execution in a separate thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    executor = _get_executor()
    result = await loop.run_in_executor(executor, _execute_sandboxed_code, code, data_dir)

    max_length = 10000
    if len(result) > max_length:
        result = result[:max_length] + f"\n\n... (output truncated, showing first {max_length} characters)"

    return result
