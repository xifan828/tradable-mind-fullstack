"""Market statistics service — historical bar analysis and current-vs-history comparisons."""

import numpy as np
import pandas as pd
from dataclasses import dataclass

from agent.services.technical.technical_indicator import TechnicalIndicatorService


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class DailyRangeContext:
    symbol: str
    lookback: int
    avg_range: float
    wide_day_threshold: float   # 75th percentile
    tight_day_threshold: float  # 25th percentile
    today_range: float
    today_status: str           # "Wide", "Normal", or "Tight"
    summary: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MarketStatisticsService:
    """Statistical analysis derived from historical daily bars.

    Compares today's market conditions to historical norms. Intended as a
    growing collection of statistical measures (range context, volume context,
    volatility regimes, etc.).
    """

    def __init__(self, symbol: str, timezone: str, asset_type: str | None = None):
        self.symbol = symbol
        self.timezone = timezone
        self.asset_type = asset_type
        self._ti = TechnicalIndicatorService(
            symbol=symbol,
            timezone=timezone,
            interval="1day",
            asset_type=asset_type,
        )

    # ------------------------------------------------------------------
    # Daily range context
    # ------------------------------------------------------------------

    def get_daily_range_context(self, lookback: int = 20, is_live: bool = True) -> DailyRangeContext:
        """Compare today's range to ATR-based historical statistics.

        Uses True Range (not simple H-L) so gaps are accounted for, making
        this safe for stocks as well as forex, crypto, and commodities.

        Args:
            lookback: Number of completed sessions used to build statistics.

        Returns:
            DailyRangeContext with avg range, wide/tight thresholds, and
            today's range classified as Wide, Normal, or Tight.
        """
        # +2: one extra bar for prev_close shift, one for today's partial bar
        df = self._ti.get_daily_bars(days=lookback + 2)

        if df is None or len(df) < 3:
            raise ValueError(
                f"Insufficient data for {self.symbol}: need at least 3 bars, got {len(df) if df is not None else 0}"
            )

        df = df.copy()

        # True Range = max(H-L, |H-prevC|, |L-prevC|)
        prev_close = df["Close"].shift(1)
        df["TR"] = np.maximum(
            df["High"] - df["Low"],
            np.maximum(
                (df["High"] - prev_close).abs(),
                (df["Low"] - prev_close).abs(),
            ),
        )

        # History: skip first row (no prev_close) and last row (today's partial bar)
        history = df.iloc[1:-1].tail(lookback)

        avg_range = float(history["TR"].mean())
        wide_threshold = float(history["TR"].quantile(0.75))
        tight_threshold = float(history["TR"].quantile(0.25))

        today = df.iloc[-1]
        today_range = float(today["TR"])

        if today_range >= wide_threshold:
            today_status = "Wide"
        elif today_range <= tight_threshold:
            today_status = "Tight"
        else:
            today_status = "Normal"

        dp = _decimal_places(avg_range)

        if is_live:
            current_range_text = f"Today's range so far is {today_range:.{dp}f}, which is {today_range / avg_range * 100:.0f}% of the average daily range."
        else:
            current_range_text = f"The last session's range was {today_range:.{dp}f}, which is {today_range / avg_range * 100:.0f}% of the average daily range."

        summary = (
            f"Over the past {lookback} sessions, {self.symbol}'s average daily range is {avg_range:.{dp}f}. "
            f"A wide day typically exceeds {wide_threshold:.{dp}f} (75th percentile) and a tight day stays below {tight_threshold:.{dp}f} (25th percentile). "
            f"{current_range_text}"
        )

        return DailyRangeContext(
            symbol=self.symbol,
            lookback=lookback,
            avg_range=round(avg_range, dp),
            wide_day_threshold=round(wide_threshold, dp),
            tight_day_threshold=round(tight_threshold, dp),
            today_range=round(today_range, dp),
            today_status=today_status,
            summary=summary,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decimal_places(value: float) -> int:
    """Infer appropriate decimal places from the magnitude of a value."""
    if value >= 10:
        return 2
    elif value >= 1:
        return 3
    elif value >= 0.1:
        return 4
    else:
        return 5