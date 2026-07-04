from twelvedata import TDClient
import pandas as pd
import talib
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Literal
import asyncio
import time

AssetType = Literal["forex", "commodity", "crypto", "stock"]


class TwelveData:

    def __init__(self, symbol: str, interval: str, outputsize: int = 400, exchange: str = None, start_date: str = None, end_date: str = None, timezone: str = "UTC", asset_type: AssetType = None):
        self.symbol = symbol
        self.interval = interval
        self.outputsize = outputsize
        self.exchange = exchange
        self.start_date = start_date
        self.end_date = end_date
        self.timezone = timezone
        self.asset_type = asset_type
        load_dotenv()
        self._init_client()

    def _init_client(self):
        api_key = os.getenv("TD_API_KEY", None)
        if not api_key:
            raise ValueError("API key for TwelveData is not set in environment variables.")
        self.client = TDClient(apikey=api_key)

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

        # Determine if we have a 'Date' column or index-based dates
        if 'Date' in df.columns:
            date_col = df['Date']
            has_date_column = True
        else:
            date_col = df.index
            has_date_column = False

        # Convert to UTC if timezone-aware
        if hasattr(date_col, 'dt'):
            if date_col.dt.tz is not None:
                dates_utc = date_col.dt.tz_convert('UTC')
            else:
                dates_utc = date_col
            day_of_week = dates_utc.dt.dayofweek  # Monday=0, Sunday=6
            hour = dates_utc.dt.hour
        else:
            # Index might be DatetimeIndex
            if date_col.tz is not None:
                dates_utc = date_col.tz_convert('UTC')
            else:
                dates_utc = date_col
            day_of_week = dates_utc.dayofweek
            hour = dates_utc.hour

        if self.interval == "1day":
            # Daily: remove Saturday (5) and Sunday (6)
            mask = ~day_of_week.isin([5, 6])
        else:
            # Intraday: forex hours filter
            # Remove: all Saturday, Friday >= 22:00, Sunday < 22:00
            is_saturday = day_of_week == 5
            is_friday_after_close = (day_of_week == 4) & (hour >= 22)
            is_sunday_before_open = (day_of_week == 6) & (hour < 22)

            mask = ~(is_saturday | is_friday_after_close | is_sunday_before_open)

        filtered_df = df[mask]

        if has_date_column:
            return filtered_df.reset_index(drop=True)
        else:
            return filtered_df

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators using TA-Lib on filtered data."""
        if df is None or df.empty or len(df) < 100:
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

    async def aget_data(self) -> pd.DataFrame:
        """Async wrapper for get_data to avoid blocking the event loop"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_data)
    
    async def aget_data_with_ti(self) -> pd.DataFrame:
        """Async wrapper for get_data_with_ti to avoid blocking the event loop"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_data_with_ti)
    
    def get_data(self) -> pd.DataFrame:
        try:
            data = self.client.time_series(
            symbol=self.symbol,
            interval=self.interval,
            outputsize=self.outputsize,
            exchange=self.exchange,
            timezone=self.timezone,
            start_date=self.start_date,
            end_date=self.end_date,
            ).as_pandas()
            if len(data.columns) > 4:
                data.columns = ["Open", "High", "Low", "Close", "Volume"]
            else:
                data.columns = ["Open", "High", "Low", "Close"]
            data = data[::-1]
            return self._filter_non_trading_hours(data)

        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def get_data_with_ti(self) -> pd.DataFrame:
        """Fetch OHLC data, filter non-trading hours, then calculate indicators using TA-Lib."""
        try:
            # For forex/commodity, fetch extra data to compensate for weekend filtering
            # Weekends are ~2/7 of the week, so fetch ~1.5x to ensure enough data after filtering
            # Also need extra for indicator warmup (EMA100 needs 100 bars)
            fetch_size = self.outputsize
            if self.asset_type in ("forex", "commodity"):
                # Fetch 1.5x + 200 extra for indicator warmup and weekend filtering
                fetch_size = int(self.outputsize * 1.5) + 200
            else:
                # For other assets, just add warmup buffer
                fetch_size = self.outputsize + 200

            # TwelveData API has a max of 5000 data points per request
            fetch_size = min(fetch_size, 5000)

            # Fetch raw OHLC data
            data = self.client.time_series(
                symbol=self.symbol,
                interval=self.interval,
                outputsize=fetch_size,
                exchange=self.exchange,
                timezone=self.timezone,
                start_date=self.start_date,
                end_date=self.end_date,
            ).as_pandas()

            # Reverse to oldest-first and reset index
            df = data[::-1].reset_index()

            # Rename columns
            df = df.rename(columns={
                "datetime": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            })

            # Keep OHLC columns, plus Volume if available
            cols = ['Date', 'Open', 'High', 'Low', 'Close']
            if 'Volume' in df.columns:
                cols.append('Volume')
            df = df[cols]

            # Filter non-trading hours first
            df = self._filter_non_trading_hours(df)

            # Calculate indicators on filtered data using TA-Lib
            df = self._calculate_indicators(df)

            # Trim to requested outputsize (keep most recent bars)
            if len(df) > self.outputsize:
                df = df.tail(self.outputsize).reset_index(drop=True)

            return df
        except Exception as e:
            print(f"Error fetching data with technical indicators: {e}")
            return None

    def calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 50) -> dict:
        """Calculate Fibonacci retracement levels from recent high/low"""
        high = df['High'].iloc[-lookback:].max()
        low = df['Low'].iloc[-lookback:].min()
        diff = high - low

        return {
            'fib_0': low,
            'fib_236': low + 0.236 * diff,
            'fib_382': low + 0.382 * diff,
            'fib_500': low + 0.5 * diff,
            'fib_618': low + 0.618 * diff,
            'fib_786': low + 0.786 * diff,
            'fib_1': high,
        }



class TimeSeriesDownloader:
    """
    Downloads large time series datasets from TwelveData by handling pagination.
    TwelveData API limits responses to 5000 datapoints per request.
    """

    MAX_BATCH_SIZE = 5000

    # Interval to timedelta mapping for calculating date offsets
    INTERVAL_DELTAS = {
        "1min": timedelta(minutes=1),
        "5min": timedelta(minutes=5),
        "15min": timedelta(minutes=15),
        "30min": timedelta(minutes=30),
        "45min": timedelta(minutes=45),
        "1h": timedelta(hours=1),
        "2h": timedelta(hours=2),
        "4h": timedelta(hours=4),
        "1day": timedelta(days=1),
        "1week": timedelta(weeks=1),
        "1month": timedelta(days=30),  # Approximate
    }

    # Datapoints per month for each interval (approximate, based on 24/5 forex market)
    # Forex: ~22 trading days/month, ~24 hours/day = ~528 hours/month
    POINTS_PER_MONTH = {
        "1min": 528 * 60,      # 31,680
        "5min": 528 * 12,      # 6,336
        "15min": 528 * 4,      # 2,112
        "30min": 528 * 2,      # 1,056
        "45min": 528 * 4 // 3, # 704
        "1h": 528,             # 528
        "2h": 264,             # 264
        "4h": 132,             # 132
        "1day": 22,            # 22
        "1week": 4,            # ~4
        "1month": 1,           # 1
    }

    def __init__(
        self,
        symbol: str,
        interval: str,
        end_date: str,
        output_size: int = None,
        months: int = None,
        exchange: str = None,
        timezone: str = "UTC",
        save_dir: str = "data/time_series"
    ):
        """
        Initialize the TimeSeriesDownloader.

        Args:
            symbol: Trading symbol (e.g., "EUR/USD", "AAPL", "BTC/USD")
            interval: Time interval (e.g., "1min", "1h", "1day")
            end_date: End date in format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            output_size: Total number of datapoints to download (ignored if months is set)
            months: Number of months of data to download (takes priority over output_size)
            exchange: Exchange name (default: None, auto-detected)
            timezone: Timezone for the data (default: "UTC")
            save_dir: Directory to save downloaded data (default: "data/time_series")
        """
        self.symbol = symbol
        self.interval = interval
        self.end_date = end_date
        self.months = months
        self.exchange = exchange
        self.timezone = timezone
        self.save_dir = Path(save_dir)

        load_dotenv()
        self._init_client()
        self._validate_interval()
        self.output_size = self._calculate_output_size(output_size, months)

    def _init_client(self):
        api_key = os.getenv("TD_API_KEY", None)
        if not api_key:
            raise ValueError("API key for TwelveData is not set in environment variables.")
        self.client = TDClient(apikey=api_key)

    def _validate_interval(self):
        if self.interval not in self.INTERVAL_DELTAS:
            raise ValueError(f"Unsupported interval: {self.interval}. Supported: {list(self.INTERVAL_DELTAS.keys())}")

    def _calculate_output_size(self, output_size: int, months: int) -> int:
        """Calculate output size from months (if provided) or use output_size directly."""
        if months is not None:
            calculated = months * self.POINTS_PER_MONTH[self.interval]
            print(f"Months: {months} -> Estimated datapoints: {calculated}")
            return calculated
        if output_size is not None:
            return output_size
        raise ValueError("Either 'months' or 'output_size' must be provided.")

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {date_str}")

    def _format_date(self, dt: datetime) -> str:
        """Format datetime to string suitable for API."""
        if self.interval in ["1day", "1week", "1month"]:
            return dt.strftime("%Y-%m-%d")
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _calculate_new_end_date(self, current_end: datetime, batch_size: int) -> datetime:
        """Calculate the new end date after fetching a batch."""
        delta = self.INTERVAL_DELTAS[self.interval]
        # Move back by batch_size intervals
        return current_end - (delta * batch_size)

    def _fetch_batch(self, end_date: str, batch_size: int) -> pd.DataFrame:
        """Fetch a single batch of data from the API."""
        try:
            data = self.client.time_series(
                symbol=self.symbol,
                interval=self.interval,
                outputsize=batch_size,
                exchange=self.exchange,
                timezone=self.timezone,
                end_date=end_date,
            ).as_pandas()

            if data is not None and not data.empty:
                data.columns = ["Open", "High", "Low", "Close"]
                return data
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching batch ending at {end_date}: {e}")
            return pd.DataFrame()

    def download(self, delay_between_requests: float = 1.0) -> pd.DataFrame:
        """
        Download the full dataset by making multiple API requests if needed.

        Args:
            delay_between_requests: Seconds to wait between API calls (default: 1.0)

        Returns:
            DataFrame with all downloaded data, sorted from oldest to newest.
        """
        all_data = []
        remaining = self.output_size
        current_end_date = self._parse_date(self.end_date)
        batch_num = 0

        print(f"Starting download: {self.symbol} @ {self.interval}")
        print(f"Target: {self.output_size} datapoints, ending at {self.end_date}")

        while remaining > 0:
            batch_size = min(remaining, self.MAX_BATCH_SIZE)
            batch_num += 1

            print(f"  Batch {batch_num}: Fetching {batch_size} points ending at {self._format_date(current_end_date)}...")

            df = self._fetch_batch(self._format_date(current_end_date), batch_size)

            if df.empty:
                print(f"  Warning: Empty response for batch {batch_num}. Stopping.")
                break

            actual_fetched = len(df)
            all_data.append(df)
            remaining -= actual_fetched

            print(f"  Batch {batch_num}: Got {actual_fetched} points. Remaining: {remaining}")

            if actual_fetched < batch_size:
                print(f"  Note: Received fewer points than requested. No more historical data available.")
                break

            if remaining > 0:
                # Get the oldest date from the current batch and move back one interval
                oldest_in_batch = df.index.min()
                if isinstance(oldest_in_batch, str):
                    oldest_in_batch = self._parse_date(oldest_in_batch)
                current_end_date = oldest_in_batch - self.INTERVAL_DELTAS[self.interval]

                time.sleep(delay_between_requests)

        if not all_data:
            print("No data downloaded.")
            return pd.DataFrame()

        # Combine all batches and sort from oldest to newest
        combined_df = pd.concat(all_data, axis=0)
        combined_df = combined_df.sort_index()
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]

        print(f"Download complete: {len(combined_df)} total datapoints")

        return combined_df

    def download_and_save(self, delay_between_requests: float = 1.0) -> Path:
        """
        Download the data and save to a CSV file.
        If the file already exists, appends new data and removes duplicates.

        Args:
            delay_between_requests: Seconds to wait between API calls (default: 1.0)

        Returns:
            Path to the saved CSV file.
        """
        df = self.download(delay_between_requests)

        if df.empty:
            raise ValueError("No data to save.")

        # Create save directory if it doesn't exist
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Generate simple filename: {pair}_{interval}.csv
        pair_clean = self.symbol.replace("/", "_")
        filename = f"{pair_clean}_{self.interval}.csv"
        filepath = self.save_dir / filename

        # If file exists, load and merge with new data
        if filepath.exists():
            print(f"Existing file found: {filepath}")
            existing_df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            print(f"  Existing data: {len(existing_df)} rows ({existing_df.index.min()} to {existing_df.index.max()})")

            # Combine existing and new data
            combined_df = pd.concat([existing_df, df], axis=0)
            # Remove duplicates based on index (datetime), keep first occurrence
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
            # Sort by datetime
            combined_df = combined_df.sort_index()

            new_rows = len(combined_df) - len(existing_df)
            print(f"  New data: {len(df)} rows, Added: {new_rows} new rows")
            print(f"  Combined: {len(combined_df)} rows ({combined_df.index.min()} to {combined_df.index.max()})")

            df = combined_df

        # Save to CSV
        df.to_csv(filepath)
        print(f"Saved to: {filepath} ({len(df)} rows)")

        return filepath


if __name__ == "__main__":
    # Example: Using TimeSeriesDownloader with months parameter
    # downloader = TimeSeriesDownloader(
    #     symbol="EUR/USD",
    #     interval="1h",
    #     months=12 * 5,  # Download 12 months of data
    #     end_date="2025-12-29",
    #     timezone="UTC",
    # )
    # filepath = downloader.download_and_save()
    # print(f"Data saved to: {filepath}")

    tw_data = TwelveData(
        symbol="EUR/USD",
       # exchange="OANDA",
        interval="1day",
        outputsize=100,
    )

    df = tw_data.get_data()
    print(df.head())
    print(df.tail(20))
