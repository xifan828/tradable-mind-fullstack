"""Market hours service for determining session status across asset types."""

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
LONDON_TZ = ZoneInfo("Europe/London")


class AssetType(str, Enum):
    FOREX = "forex"
    COMMODITY = "commodity"
    CRYPTO = "crypto"
    STOCK = "stock"


@dataclass
class MarketStatus:
    asset_type: AssetType
    is_open: bool
    stage: str                  # "Asian", "London", "London/New York", "New York", "Off-hours", or "closed"
    hours_open: float           # hours since session open (0 if closed)
    hours_until_ny_close: float # hours until NY session close (0 if closed)
    session_duration_hours: float
    description: str


def _hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def _trading_session(utc_now: datetime) -> str:
    """Return the named trading session for the given UTC time.

    Derived from actual local clock times so DST is handled correctly:
      London open:  08:00 Europe/London  (07:00 UTC in BST, 08:00 UTC in GMT)
      London close: 17:00 Europe/London  (16:00 UTC in BST, 17:00 UTC in GMT)
      NY open:      08:00 America/New_York (12:00 UTC in EDT, 13:00 UTC in EST)
      NY close:     17:00 America/New_York (21:00 UTC in EDT, 22:00 UTC in EST)

    Sessions:
      London open, NY closed  -> London
      London open, NY open    -> London/New York  (overlap)
      London closed, NY open  -> New York
      Both closed             -> Asian
    """
    london_now = utc_now.astimezone(LONDON_TZ)
    ny_now = utc_now.astimezone(NY_TZ)

    london_open  = london_now.replace(hour=8,  minute=0, second=0, microsecond=0)
    london_close = london_now.replace(hour=17, minute=0, second=0, microsecond=0)
    ny_open      = ny_now.replace(hour=8,  minute=0, second=0, microsecond=0)
    ny_close     = ny_now.replace(hour=17, minute=0, second=0, microsecond=0)

    london_active = london_open <= london_now < london_close
    ny_active     = ny_open <= ny_now < ny_close

    if london_active and ny_active:
        return "London/New York"
    elif london_active:
        return "London"
    elif ny_active:
        return "New York"
    else:
        return "Asian"


class MarketHoursService:
    """
    Given the current UTC time, describes the session status for a given asset type.

    Session definitions (all times in New York local time):
      - Forex:     Opens 5:00 PM NY, runs 24 hours (closes 5:00 PM NY next day)
      - Commodity: Opens 6:00 PM NY, closes 5:00 PM NY next day (~23 hours)
      - Crypto:    Opens 00:00 UTC, runs 24 hours (always open)
      - Stock (US):Opens 9:30 AM NY, closes 4:00 PM NY (Mon–Fri only)
    """

    def get_status(self, asset_type: AssetType | str, utc_now: datetime | None = None) -> MarketStatus:
        if not isinstance(asset_type, AssetType):
            asset_type = AssetType(asset_type)
        if utc_now is None:
            utc_now = datetime.now(timezone.utc)
        elif utc_now.tzinfo is None:
            utc_now = utc_now.replace(tzinfo=timezone.utc)

        match asset_type:
            case AssetType.FOREX:
                return self._forex_status(utc_now)
            case AssetType.COMMODITY:
                return self._commodity_status(utc_now)
            case AssetType.CRYPTO:
                return self._crypto_status(utc_now)
            case AssetType.STOCK:
                return self._stock_status(utc_now)
            case _:
                raise ValueError(f"Unsupported asset type: {asset_type}")

    # ------------------------------------------------------------------
    # Forex: opens 5 PM NY Sunday, closes 5 PM NY Friday (24/5)
    # ------------------------------------------------------------------
    def _forex_status(self, utc_now: datetime) -> MarketStatus:
        ny_now = utc_now.astimezone(NY_TZ)
        session_duration = 24.0
        weekday = ny_now.weekday()  # 0=Mon … 6=Sun

        at_5pm = ny_now.replace(hour=17, minute=0, second=0, microsecond=0)

        # Weekend: Fri >= 5 PM through Sun < 5 PM
        is_weekend = (
            (weekday == 4 and ny_now >= at_5pm) or  # Friday after close
            weekday == 5 or                          # Saturday
            (weekday == 6 and ny_now < at_5pm)       # Sunday before open
        )
        if is_weekend:
            # Next open: Sunday 5 PM NY
            days_to_sunday = (6 - weekday) % 7
            next_open = at_5pm + timedelta(days=days_to_sunday)
            if weekday == 6:
                next_open = at_5pm  # this Sunday 5 PM
            hours_until = _hours_between(utc_now, next_open)
            utc_str = utc_now.strftime("%A %b %d, %H:%M UTC")
            desc = f"Forex market is closed (weekend) - {utc_str}. Reopens Sunday 5:00 PM NY in ~{hours_until:.1f}h."
            return MarketStatus(
                asset_type=AssetType.FOREX,
                is_open=False,
                stage="closed",
                hours_open=0.0,
                hours_until_ny_close=0.0,
                session_duration_hours=session_duration,
                description=desc,
            )

        # Session open: most recent 5 PM NY (same day if past 5 PM, else yesterday)
        if ny_now >= at_5pm:
            session_open = at_5pm
        else:
            session_open = at_5pm - timedelta(days=1)

        # Session close: next Friday 5 PM NY if today is Friday, else tomorrow 5 PM
        session_close = session_open + timedelta(hours=session_duration)

        hours_open = _hours_between(session_open, utc_now)
        hours_until_close = _hours_between(utc_now, session_close)
        session = _trading_session(utc_now)
        utc_str = utc_now.strftime("%H:%M UTC")

        desc = (
            f"It is currently {utc_str}, which is the {session} session. "
            f"The forex market has been open for {hours_open:.1f}h, "
            f"with {hours_until_close:.1f}h remaining until today's NY 5 PM close."
        )
        return MarketStatus(
            asset_type=AssetType.FOREX,
            is_open=True,
            stage=session,
            hours_open=round(hours_open, 2),
            hours_until_ny_close=round(hours_until_close, 2),
            session_duration_hours=session_duration,
            description=desc,
        )

    # ------------------------------------------------------------------
    # Commodity: opens 6 PM NY Sunday, closes 5 PM NY Friday (~23h/day)
    # 1-hour maintenance break daily: 5 PM – 6 PM NY
    # ------------------------------------------------------------------
    def _commodity_status(self, utc_now: datetime) -> MarketStatus:
        ny_now = utc_now.astimezone(NY_TZ)
        session_duration = 23.0  # 6 PM → 5 PM next day
        weekday = ny_now.weekday()  # 0=Mon … 6=Sun

        at_5pm = ny_now.replace(hour=17, minute=0, second=0, microsecond=0)
        at_6pm = ny_now.replace(hour=18, minute=0, second=0, microsecond=0)

        # Weekend: Fri >= 5 PM through Sun < 6 PM
        is_weekend = (
            (weekday == 4 and ny_now >= at_5pm) or  # Friday after close
            weekday == 5 or                          # Saturday
            (weekday == 6 and ny_now < at_6pm)       # Sunday before open
        )
        if is_weekend:
            days_to_sunday = (6 - weekday) % 7
            next_open_day = at_6pm + timedelta(days=days_to_sunday)
            if weekday == 6:
                next_open_day = at_6pm  # this Sunday 6 PM
            hours_until = _hours_between(utc_now, next_open_day)
            utc_str = utc_now.strftime("%A %b %d, %H:%M UTC")
            desc = f"Commodity market is closed (weekend) - {utc_str}. Reopens Sunday 6:00 PM NY in ~{hours_until:.1f}h."
            return MarketStatus(
                asset_type=AssetType.COMMODITY,
                is_open=False,
                stage="closed",
                hours_open=0.0,
                hours_until_ny_close=0.0,
                session_duration_hours=session_duration,
                description=desc,
            )

        open_candidate = at_6pm
        close_candidate = at_5pm

        # Determine session boundaries and maintenance break
        # Case A: midnight – 5 PM → session opened yesterday 6 PM, closes today 5 PM
        # Case B: 6 PM – midnight → session opened today 6 PM, closes tomorrow 5 PM
        # Case C: 5 PM – 6 PM → 1-hour maintenance break
        if ny_now.hour < 17:
            session_open = open_candidate - timedelta(days=1)
            session_close = close_candidate
        elif ny_now >= at_6pm:
            session_open = open_candidate
            session_close = close_candidate + timedelta(days=1)
        else:
            # 5 PM – 6 PM maintenance break
            minutes_until_open = int((at_6pm - ny_now).total_seconds() / 60)
            utc_str = utc_now.strftime("%A %b %d, %H:%M UTC")
            desc = (
                f"Commodity market is closed (maintenance break) - {utc_str}. "
                f"Opens in ~{minutes_until_open} minutes at 6:00 PM NY."
            )
            return MarketStatus(
                asset_type=AssetType.COMMODITY,
                is_open=False,
                stage="closed",
                hours_open=0.0,
                hours_until_ny_close=0.0,
                session_duration_hours=session_duration,
                description=desc,
            )

        hours_open = _hours_between(session_open, utc_now)
        hours_until_close = _hours_between(utc_now, session_close)
        session = _trading_session(utc_now)
        utc_str = utc_now.strftime("%H:%M UTC")

        desc = (
            f"It is currently {utc_str}, which is the {session} session. "
            f"The commodity market has been open for {hours_open:.1f}h, "
            f"with {hours_until_close:.1f}h remaining until today's NY 5 PM close."
        )
        return MarketStatus(
            asset_type=AssetType.COMMODITY,
            is_open=True,
            stage=session,
            hours_open=round(hours_open, 2),
            hours_until_ny_close=round(hours_until_close, 2),
            session_duration_hours=session_duration,
            description=desc,
        )

    # ------------------------------------------------------------------
    # Crypto: opens 00:00 UTC, always 24 hours
    # ------------------------------------------------------------------
    def _crypto_status(self, utc_now: datetime) -> MarketStatus:
        session_duration = 24.0
        session_open = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
        session_close = session_open + timedelta(days=1)

        hours_open = _hours_between(session_open, utc_now)
        hours_until_close = _hours_between(utc_now, session_close)

        # "NY close" for crypto: use 4 PM NY as reference (end of US equity day)
        ny_now = utc_now.astimezone(NY_TZ)
        ny_close = ny_now.replace(hour=16, minute=0, second=0, microsecond=0)
        if ny_now >= ny_close:
            ny_close += timedelta(days=1)
        hours_until_ny_close = _hours_between(utc_now, ny_close)

        session = _trading_session(utc_now)
        utc_str = utc_now.strftime("%H:%M UTC")
        desc = (
            f"It is currently {utc_str}, which is the {session} session. "
            f"Crypto is always open — today's UTC day is {hours_open:.1f}h in, "
            f"with {hours_until_ny_close:.1f}h until the NY 4 PM equity close reference."
        )
        return MarketStatus(
            asset_type=AssetType.CRYPTO,
            is_open=True,
            stage=session,
            hours_open=round(hours_open, 2),
            hours_until_ny_close=round(hours_until_ny_close, 2),
            session_duration_hours=session_duration,
            description=desc,
        )

    # ------------------------------------------------------------------
    # Stock (US): 9:30 AM – 4:00 PM NY, Mon–Fri
    # ------------------------------------------------------------------
    def _stock_status(self, utc_now: datetime) -> MarketStatus:
        session_duration = 6.5  # 9:30 AM → 4:00 PM
        ny_now = utc_now.astimezone(NY_TZ)
        weekday = ny_now.weekday()  # 0=Mon, 6=Sun

        market_open = ny_now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_now.replace(hour=16, minute=0, second=0, microsecond=0)

        utc_str = utc_now.strftime("%H:%M UTC")

        if weekday >= 5:  # Saturday or Sunday
            next_monday_open = market_open + timedelta(days=(7 - weekday))
            hours_until = _hours_between(utc_now, next_monday_open)
            utc_str_full = utc_now.strftime("%A %b %d, %H:%M UTC")
            desc = (
                f"US stock market is closed (weekend) - {utc_str_full}. "
                f"Opens Monday 9:30 AM NY in ~{hours_until:.1f}h."
            )
            return MarketStatus(
                asset_type=AssetType.STOCK,
                is_open=False,
                stage="closed",
                hours_open=0.0,
                hours_until_ny_close=0.0,
                session_duration_hours=session_duration,
                description=desc,
            )

        if ny_now < market_open:
            hours_until = _hours_between(utc_now, market_open)
            desc = f"US stock market is closed (pre-market) - {utc_str}. Opens in ~{hours_until:.1f}h at 9:30 AM NY."
            return MarketStatus(
                asset_type=AssetType.STOCK,
                is_open=False,
                stage="closed",
                hours_open=0.0,
                hours_until_ny_close=0.0,
                session_duration_hours=session_duration,
                description=desc,
            )

        if ny_now >= market_close:
            # After close - find next trading day open
            days_ahead = 1
            if weekday == 4:  # Friday → Monday
                days_ahead = 3
            next_open = market_open + timedelta(days=days_ahead)
            hours_until = _hours_between(utc_now, next_open)
            desc = f"US stock market is closed (after-hours) - {utc_str}. Next open in ~{hours_until:.1f}h."
            return MarketStatus(
                asset_type=AssetType.STOCK,
                is_open=False,
                stage="closed",
                hours_open=0.0,
                hours_until_ny_close=0.0,
                session_duration_hours=session_duration,
                description=desc,
            )

        # Market is open
        hours_open = _hours_between(market_open, utc_now)
        hours_until_close = _hours_between(utc_now, market_close)

        desc = (
            f"It is currently {utc_str}, which is the New York session. "
            f"The US stock market has been open for {hours_open:.1f}h, "
            f"with {hours_until_close:.1f}h remaining until today's 4:00 PM NY close."
        )
        return MarketStatus(
            asset_type=AssetType.STOCK,
            is_open=True,
            stage="New York",
            hours_open=round(hours_open, 2),
            hours_until_ny_close=round(hours_until_close, 2),
            session_duration_hours=session_duration,
            description=desc,
        )

