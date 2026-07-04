"""Session snapshot service — provides today's (or last) session OHLC summary."""

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from zoneinfo import ZoneInfo
from twelvedata import TDClient
import pandas as pd
import os
from dotenv import load_dotenv

from agent.services.market_hours.market_hours import MarketHoursService, AssetType, MarketStatus

NY_TZ = ZoneInfo("America/New_York")


@dataclass
class SessionContext:
    symbol: str
    asset_type: AssetType
    session_label: str      # "Today" or "Last Session (Fri Mar 15)"
    open: float
    high: float
    low: float
    close: float            # current price if live, final close if closed
    change: float           # close - open
    change_pct: float       # percentage
    is_live: bool
    summary: str            # human-readable multi-line string


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(value: float) -> str:
    """Format a price value with appropriate decimal places."""
    abs_val = abs(value)
    if abs_val >= 100:
        return f"{value:,.2f}"
    elif abs_val >= 1:
        return f"{value:.4f}"
    else:
        return f"{value:.6f}"


def _fmt_change(change: float, pct: float) -> str:
    sign = "+" if change >= 0 else ""
    arrow = "^" if change >= 0 else "v"
    return f"{arrow} {sign}{_fmt(change)}  ({sign}{pct:.2f}%)"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SessionContextService:
    """
    Returns today's session OHLC snapshot, or the last completed session if the
    market is currently closed. Session boundaries match MarketHoursService:

      Forex     : 5 PM NY → 5 PM NY  (Mon–Fri)
      Commodity : 6 PM NY → 5 PM NY  (Mon–Fri, 1h daily break)
      Crypto    : 00:00 UTC → 00:00 UTC  (always open)
      Stock     : 9:30 AM NY → 4:00 PM NY  (Mon–Fri)
    """

    def __init__(self):
        load_dotenv()
        api_key = os.getenv("TD_API_KEY")
        if not api_key:
            raise ValueError("TD_API_KEY not set in environment")
        self.client = TDClient(apikey=api_key)
        self.market_hours = MarketHoursService()

    def get_snapshot(
        self,
        symbol: str,
        asset_type: AssetType | str,
        exchange: str = None,
        utc_now: datetime = None,
    ) -> SessionContext:
        if not isinstance(asset_type, AssetType):
            asset_type = AssetType(asset_type)
        if utc_now is None:
            utc_now = datetime.now(timezone.utc)
        elif utc_now.tzinfo is None:
            utc_now = utc_now.replace(tzinfo=timezone.utc)

        status = self.market_hours.get_status(asset_type, utc_now)

        if asset_type == AssetType.STOCK:
            return self._stock_snapshot(symbol, exchange, utc_now, status)
        return self._intraday_snapshot(symbol, asset_type, exchange, utc_now, status)

    # ------------------------------------------------------------------
    # Session window resolution
    # ------------------------------------------------------------------

    def _forex_window(self, utc_now: datetime) -> tuple[datetime, datetime, bool, str]:
        ny_now = utc_now.astimezone(NY_TZ)
        weekday = ny_now.weekday()
        at_5pm_ny = ny_now.replace(hour=17, minute=0, second=0, microsecond=0)
        at_5pm_utc = at_5pm_ny.astimezone(timezone.utc)

        is_weekend = (
            (weekday == 4 and utc_now >= at_5pm_utc) or
            weekday == 5 or
            (weekday == 6 and utc_now < at_5pm_utc)
        )

        if is_weekend:
            # Last session started Thu 5 PM NY — take 24 bars from there
            days_since_fri = (weekday - 4) % 7
            fri_5pm_ny = at_5pm_ny - timedelta(days=days_since_fri)
            thu_5pm_utc = fri_5pm_ny.astimezone(timezone.utc) - timedelta(hours=24)
            label = f"Last Session ({fri_5pm_ny.strftime('%a %b %d')})"
            return thu_5pm_utc, False, label

        # Current session started at last 5 PM NY
        if utc_now >= at_5pm_utc:
            session_start_utc = at_5pm_utc
        else:
            session_start_utc = at_5pm_utc - timedelta(hours=24)
        return session_start_utc, True, "Today"

    def _commodity_window(self, utc_now: datetime) -> tuple[datetime, bool, str]:
        ny_now = utc_now.astimezone(NY_TZ)
        weekday = ny_now.weekday()
        at_5pm_ny = ny_now.replace(hour=17, minute=0, second=0, microsecond=0)
        at_6pm_ny = ny_now.replace(hour=18, minute=0, second=0, microsecond=0)
        at_5pm_utc = at_5pm_ny.astimezone(timezone.utc)
        at_6pm_utc = at_6pm_ny.astimezone(timezone.utc)

        is_weekend = (
            (weekday == 4 and utc_now >= at_5pm_utc) or
            weekday == 5 or
            (weekday == 6 and utc_now < at_6pm_utc)
        )

        if is_weekend:
            # Last session started Thu 6 PM NY — take 23 bars from there
            days_since_fri = (weekday - 4) % 7
            fri_5pm_ny = at_5pm_ny - timedelta(days=days_since_fri)
            thu_6pm_utc = (fri_5pm_ny.replace(hour=18) - timedelta(days=1)).astimezone(timezone.utc)
            label = f"Last Session ({fri_5pm_ny.strftime('%a %b %d')})"
            return thu_6pm_utc, False, label

        # Maintenance break (5 PM–6 PM): show last completed session (23 bars from yesterday 6 PM)
        if at_5pm_utc <= utc_now < at_6pm_utc:
            yesterday_6pm_utc = at_6pm_utc - timedelta(hours=24)
            label = f"Last Session ({at_5pm_ny.strftime('%a %b %d')})"
            return yesterday_6pm_utc, False, label

        # Active session started at last 6 PM NY
        if utc_now >= at_6pm_utc:
            session_start_utc = at_6pm_utc
        else:
            session_start_utc = at_6pm_utc - timedelta(hours=24)
        return session_start_utc, True, "Today"

    def _crypto_window(self, utc_now: datetime) -> tuple[datetime, bool, str]:
        session_start = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return session_start, True, "Today"

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_hourly(self, symbol: str, exchange: str, outputsize: int = 96) -> pd.DataFrame | None:
        try:
            data = self.client.time_series(
                symbol=symbol,
                interval="1h",
                outputsize=outputsize,
                exchange=exchange,
                timezone="UTC",
            ).as_pandas()
            if data is None or data.empty:
                return None
            data = data[::-1].reset_index()
            data = data.rename(columns={
                "datetime": "Date", "open": "Open",
                "high": "High", "low": "Low", "close": "Close",
            })
            data["Date"] = pd.to_datetime(data["Date"], utc=True)
            for col in ("Open", "High", "Low", "Close"):
                data[col] = pd.to_numeric(data[col])
            return data
        except Exception as e:
            raise RuntimeError(f"Failed to fetch hourly data for {symbol}: {e}")

    def _aggregate(
        self, df: pd.DataFrame, start_utc: datetime, max_bars: int
    ) -> tuple[float, float, float, float] | None:
        """
        Starting from the bar whose timestamp == start_utc, take up to max_bars
        consecutive hourly bars. Each 1h bar timestamped T covers [T, T+59:59], so
        the bar AT the session open is bar 1, and we never accidentally include the
        first bar of the next session.
        """
        session = df[df["Date"] >= start_utc].head(max_bars)
        if session.empty:
            return None
        return (
            float(session["Open"].iloc[0]),
            float(session["High"].max()),
            float(session["Low"].min()),
            float(session["Close"].iloc[-1]),
        )

    # ------------------------------------------------------------------
    # Snapshot builders
    # ------------------------------------------------------------------

    # bars per session: forex 24h, commodity 23h (6 PM–5 PM with 1h break), crypto 24h
    _SESSION_BARS = {
        AssetType.FOREX: 24,
        AssetType.COMMODITY: 23,
        AssetType.CRYPTO: 24,
    }

    def _intraday_snapshot(
        self,
        symbol: str,
        asset_type: AssetType,
        exchange: str,
        utc_now: datetime,
        status: MarketStatus,
    ) -> SessionContext:
        match asset_type:
            case AssetType.FOREX:
                start, is_live, label = self._forex_window(utc_now)
            case AssetType.COMMODITY:
                start, is_live, label = self._commodity_window(utc_now)
            case AssetType.CRYPTO:
                start, is_live, label = self._crypto_window(utc_now)
            case _:
                raise ValueError(f"Unsupported intraday type: {asset_type}")

        max_bars = self._SESSION_BARS[asset_type]

        # Fetch enough hourly bars to cover one full session + buffer for lookback
        df = self._fetch_hourly(symbol, exchange, outputsize=max_bars + 48)

        result = self._aggregate(df, start, max_bars)
        if result is None:
            raise RuntimeError(f"No session bars found for {symbol} in window [{start}, {end}]")

        open_, high, low, close = result
        change = close - open_
        change_pct = (change / open_ * 100) if open_ else 0.0

        return SessionContext(
            symbol=symbol,
            asset_type=asset_type,
            session_label=label,
            open=open_,
            high=high,
            low=low,
            close=close,
            change=change,
            change_pct=change_pct,
            is_live=is_live,
            summary=self._build_summary(symbol, asset_type, label, is_live, open_, high, low, close, change, change_pct, status),
        )

    def _stock_snapshot(
        self,
        symbol: str,
        exchange: str,
        utc_now: datetime,
        status: MarketStatus,
    ) -> SessionContext:
        try:
            data = self.client.time_series(
                symbol=symbol,
                interval="1day",
                outputsize=5,
                exchange=exchange,
                timezone="America/New_York",
            ).as_pandas()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch daily data for {symbol}: {e}")

        if data is None or data.empty:
            raise RuntimeError(f"No data returned for {symbol}")

        data = data[::-1]
        data.columns = (
            ["Open", "High", "Low", "Close"]
            if len(data.columns) == 4
            else ["Open", "High", "Low", "Close", "Volume"]
        )
        for col in ("Open", "High", "Low", "Close"):
            data[col] = pd.to_numeric(data[col])

        row = data.iloc[-1]
        is_live = status.is_open
        try:
            date_str = data.index[-1].strftime("%a %b %d")
        except Exception:
            date_str = str(data.index[-1])
        label = "Today" if is_live else f"Last Session ({date_str})"

        open_ = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        change = close - open_
        change_pct = (change / open_ * 100) if open_ else 0.0

        return SessionContext(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            session_label=label,
            open=open_,
            high=high,
            low=low,
            close=close,
            change=change,
            change_pct=change_pct,
            is_live=is_live,
            summary=self._build_summary(symbol, AssetType.STOCK, label, is_live, open_, high, low, close, change, change_pct, status),
        )

    # ------------------------------------------------------------------
    # Summary formatter
    # ------------------------------------------------------------------

    def _build_summary(
        self,
        symbol: str,
        asset_type: AssetType,
        label: str,
        is_live: bool,
        open_: float,
        high: float,
        low: float,
        close: float,
        change: float,
        change_pct: float,
        status: MarketStatus,
    ) -> str:
        live_tag = "[LIVE]" if is_live else "[CLOSED]"
        type_name = asset_type.value.title()
        close_label = "Now " if is_live else "Close"

        sign = "+" if change >= 0 else ""
        line1 = f"{symbol}  ·  {type_name}  ·  {label}  {live_tag}"
        line2 = (
            f"Open: {_fmt(open_)}\n"
            f"High: {_fmt(high)}\n"
            f"Low: {_fmt(low)}\n"
            f"{close_label}: {_fmt(close)}\n"
            f"Change: {sign}{_fmt(change)}\n"
            f"Percent: {sign}{change_pct:.2f}%"
        )
        line3 = status.description

        return f"{line1}\n{line2}\n{line3}"