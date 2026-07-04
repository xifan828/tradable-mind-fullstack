import yfinance as yf
import pandas as pd
import talib
import pytz
from typing import Literal, Optional

AssetType = Literal["forex", "commodity", "crypto", "stock"]


class YFinanceData:
    """Data source using yfinance for indices, yields, and assets not on TwelveData.

    Supported assets include:
    - Dollar Index: DX-Y.NYB
    - Treasury Yields: ^TNX (10Y), ^TYX (30Y), ^FVX (5Y), ^IRX (13-week)
    - Major indices: ^GSPC (S&P 500), ^DJI (Dow), ^IXIC (Nasdaq)
    """

    # Interval mapping (TwelveData format → yfinance format)
    INTERVAL_MAP = {
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1h": "1h",
        "4h": "4h",
        "1day": "1d",
        "1week": "1wk",
    }

    def __init__(
        self,
        symbol: str,
        interval: str,
        outputsize: int = 400,
        timezone: str = "UTC",
        asset_type: AssetType = None,
    ):
        """Initialize YFinanceData.

        Args:
            symbol: yfinance ticker symbol (e.g., "DX-Y.NYB", "^TNX")
            interval: Time interval in TwelveData format (e.g., "1h", "4h", "1day")
            outputsize: Number of data points to fetch (approximate)
            timezone: Target timezone for the data
            asset_type: Asset type for trading hours filtering ("forex", "commodity", "crypto", "stock")
        """
        self.symbol = symbol
        self.original_interval = interval  # Keep original for filtering logic
        self.interval = self._map_interval(interval)
        self.outputsize = outputsize
        self.timezone = timezone
        self.asset_type = asset_type

    def _map_interval(self, interval: str) -> str:
        """Map TwelveData interval format to yfinance format."""
        if interval not in self.INTERVAL_MAP:
            raise ValueError(
                f"Unsupported interval: {interval}. "
                f"Supported: {list(self.INTERVAL_MAP.keys())}"
            )
        yf_interval = self.INTERVAL_MAP[interval]
        if yf_interval is None:
            raise ValueError(f"Interval {interval} is not supported by yfinance")
        return yf_interval

    def _calculate_period(self) -> str:
        """Calculate yfinance period based on outputsize and interval.

        yfinance uses period (like "1y", "6mo") instead of outputsize.
        This method estimates the period needed to get approximately
        the requested number of data points.
        """
        interval = self.interval
        outputsize = self.outputsize

        # yfinance data limits by interval:
        # 1m: 7 days max
        # 5m-30m: 60 days max
        # 1h, 4h: ~2 years (730 days)
        # 1d, 1wk: max available

        if interval == "1m":
            # 1 minute data limited to 7 days
            return "7d"
        elif interval in ["5m", "15m", "30m"]:
            # Intraday (except 1m) limited to 60 days
            return "60d"
        elif interval in ["1h", "4h"]:
            # Hourly/4-hourly data: ~730 days max, use 2y for simplicity
            # 4h with period="1y" returns ~1500+ bars
            bars_per_day = 24 if interval == "1h" else 6
            days_needed = (outputsize // bars_per_day) + 1
            days_needed = min(days_needed, 730)
            if days_needed > 365:
                return "2y"
            elif days_needed > 180:
                return "1y"
            elif days_needed > 90:
                return "6mo"
            elif days_needed > 30:
                return "3mo"
            else:
                return "1mo"
        else:
            # Daily/weekly: use max period for best coverage
            return "max"

    def _convert_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame Date column to target timezone."""
        if df.empty:
            return df

        target_tz = pytz.timezone(self.timezone)

        if df['Date'].dt.tz is not None:
            # Already timezone-aware, convert to target
            df['Date'] = df['Date'].dt.tz_convert(target_tz)
        else:
            # Timezone-naive, assume UTC and convert
            df['Date'] = df['Date'].dt.tz_localize('UTC').dt.tz_convert(target_tz)

        # Remove timezone info for consistency with TwelveData output
        df['Date'] = df['Date'].dt.tz_localize(None)

        return df

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators using talib to match TwelveData output."""
        if df.empty or len(df) < 100:
            # Need enough data for EMA100
            return df

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values

        # EMAs
        df['EMA10'] = talib.EMA(close, timeperiod=10)
        df['EMA20'] = talib.EMA(close, timeperiod=20)
        df['EMA50'] = talib.EMA(close, timeperiod=50)
        df['EMA100'] = talib.EMA(close, timeperiod=100)

        # Bollinger Bands
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = talib.BBANDS(
            close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )

        # MACD
        df['MACD'], df['MACD_Signal'], df['MACD_Diff'] = talib.MACD(
            close, fastperiod=12, slowperiod=26, signalperiod=9
        )

        # RSI
        df['RSI14'] = talib.RSI(close, timeperiod=14)

        # ATR
        df['ATR'] = talib.ATR(high, low, close, timeperiod=14)

        # ROC
        df['ROC12'] = talib.ROC(close, timeperiod=12)

        return df

    def _filter_non_trading_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out non-trading hours for forex/commodity assets.

        Forex/commodity markets are closed:
        - Daily interval: Saturday and Sunday
        - Intraday: All Saturday, Friday >= 22:00 UTC, Sunday < 22:00 UTC
        """
        if self.asset_type not in ("forex", "commodity"):
            return df

        if df is None or df.empty:
            return df

        # Get the date column
        date_col = df['Date']

        # Convert to UTC if timezone-aware
        if date_col.dt.tz is not None:
            dates_utc = date_col.dt.tz_convert('UTC')
        else:
            dates_utc = date_col

        day_of_week = dates_utc.dt.dayofweek  # Monday=0, Sunday=6
        hour = dates_utc.dt.hour

        if self.original_interval == "1day":
            # Daily: remove Saturday (5) and Sunday (6)
            mask = ~day_of_week.isin([5, 6])
        else:
            # Intraday: forex hours filter
            # Remove: all Saturday, Friday >= 22:00, Sunday < 22:00
            is_saturday = day_of_week == 5
            is_friday_after_close = (day_of_week == 4) & (hour >= 22)
            is_sunday_before_open = (day_of_week == 6) & (hour < 22)

            mask = ~(is_saturday | is_friday_after_close | is_sunday_before_open)

        return df[mask].reset_index(drop=True)

    def get_data(self) -> Optional[pd.DataFrame]:
        """Fetch OHLC data from yfinance without technical indicators."""
        try:
            ticker = yf.Ticker(self.symbol)
            period = self._calculate_period()

            df = ticker.history(period=period, interval=self.interval)

            if df is None or df.empty:
                print(f"No data returned from yfinance for {self.symbol}")
                return None

            # Reset index to get Date as column
            df = df.reset_index()

            # Rename columns to match TwelveData format
            # yfinance uses 'Date' for daily, 'Datetime' for intraday
            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            df = df.rename(columns={date_col: 'Date'})

            # Keep only OHLC columns
            df = df[['Date', 'Open', 'High', 'Low', 'Close']]

            # Convert timezone
            df = self._convert_timezone(df)

            # Limit to outputsize
            if len(df) > self.outputsize:
                df = df.tail(self.outputsize).reset_index(drop=True)

            # Filter non-trading hours for forex/commodity
            df = self._filter_non_trading_hours(df)

            return df

        except Exception as e:
            print(f"Error fetching data from yfinance: {e}")
            return None

    def get_data_with_ti(self) -> Optional[pd.DataFrame]:
        """Fetch OHLC data from yfinance with pre-calculated technical indicators.

        Returns DataFrame with columns matching TwelveData output:
        Date, Open, High, Low, Close, EMA10, EMA20, EMA50, EMA100,
        BB_Upper, BB_Middle, BB_Lower, MACD, MACD_Signal, MACD_Diff,
        RSI14, ATR, ROC12
        """
        try:
            ticker = yf.Ticker(self.symbol)
            period = self._calculate_period()

            df = ticker.history(period=period, interval=self.interval)

            if df is None or df.empty:
                print(f"No data returned from yfinance for {self.symbol}")
                return None

            # Reset index to get Date as column
            df = df.reset_index()

            # Rename columns to match TwelveData format
            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            df = df.rename(columns={date_col: 'Date'})

            # Keep only OHLC columns
            df = df[['Date', 'Open', 'High', 'Low', 'Close']]

            # Convert timezone
            df = self._convert_timezone(df)

            # Calculate technical indicators
            df = self._calculate_indicators(df)

            # Limit to outputsize (from the end to get most recent data)
            if len(df) > self.outputsize:
                df = df.tail(self.outputsize).reset_index(drop=True)

            # Filter non-trading hours for forex/commodity
            df = self._filter_non_trading_hours(df)

            return df

        except Exception as e:
            print(f"Error fetching data with indicators from yfinance: {e}")
            return None


if __name__ == "__main__":
    # Test with Dollar Index
    yf_data = YFinanceData(
        symbol="DX-Y.NYB",
        interval="1day",
        outputsize=100,
        timezone="UTC"
    )
    df = yf_data.get_data_with_ti()
    if df is not None:
        print(f"Downloaded {len(df)} rows for DX-Y.NYB")
        print(f"Columns: {df.columns.tolist()}")
        print(df.tail())

    # Test with 10-Year Treasury Yield
    yf_data_tnx = YFinanceData(
        symbol="^TNX",
        interval="1day",
        outputsize=100,
        timezone="UTC"
    )
    df_tnx = yf_data_tnx.get_data_with_ti()
    if df_tnx is not None:
        print(f"\nDownloaded {len(df_tnx)} rows for ^TNX")
        print(df_tnx.tail())
