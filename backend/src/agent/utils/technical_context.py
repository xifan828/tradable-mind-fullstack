import pandas as pd

class TechnicalIndicators:
    def __init__(self):
        pass
    
    @staticmethod
    def get_context(df: pd.DataFrame, decimal_places: int, analysis_type: str, period: int = 20) -> str:
        analysis_type = analysis_type.lower()
        if analysis_type == "ema":
            return TechnicalIndicators.get_ma_context(df, decimal_places, period)
        elif analysis_type == "macd":
            return TechnicalIndicators.get_macd_context(df, decimal_places, period)
        elif analysis_type == "atr":
            return TechnicalIndicators.get_atr_context(df, decimal_places)
        elif analysis_type == "rsi":
            return TechnicalIndicators.get_rsi_context(df, decimal_places)
        elif analysis_type in ["bb", "pivot", "fibonacci", "normal"]:
            return ""
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")
    
    # @staticmethod
    # def calculate_technical_indicators(df, sma=False, ema=True, rsi=True, macd=True, roc=True, bbands=True, atr=True) -> pd.DataFrame:
    #     df = df.copy()

    #     # Ensure the index is a DateTimeIndex
    #     if not isinstance(df.index, pd.DatetimeIndex):
    #         raise ValueError("DataFrame index must be a DateTimeIndex")

    #     # --- Simple Moving Average (SMA) ---
    #     if sma:
    #         df['SMA10'] = ta.trend.sma_indicator(df['Close'], window=10)
    #         df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
    #         df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
    #         df['SMA100'] = ta.trend.sma_indicator(df['Close'], window=100)

    #     # --- Exponential Moving Average (EMA) ---
    #     if ema:
    #         df['EMA10'] = ta.trend.ema_indicator(df['Close'], window=10)
    #         df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
    #         df['EMA50'] = ta.trend.ema_indicator(df['Close'], window=50)
    #         df['EMA100'] = ta.trend.ema_indicator(df['Close'], window=100)

    #     # --- Relative Strength Index (RSI) ---
    #     if rsi:
    #         df['RSI14'] = ta.momentum.rsi(df['Close'], window=14)

    #     # --- Moving Average Convergence Divergence (MACD) ---
    #     if macd:
    #         macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    #         df['MACD'] = macd.macd()
    #         df['MACD_Signal'] = macd.macd_signal()
    #         df['MACD_Diff'] = macd.macd_diff()  # This is the MACD Histogram

    #     # --- Rate of Change (ROC) ---
    #     if roc:
    #         df['ROC12'] = ta.momentum.roc(df['Close'], window=12)

    #     # --- Bollinger Bands (Default: 20 SMA, ±2 std) ---
    #     if bbands:
    #         bollinger = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    #         df['BB_Mid']   = bollinger.bollinger_mavg()   # Middle band (20 SMA by default)
    #         df['BB_Upper'] = bollinger.bollinger_hband()  # Upper band (+2 std)
    #         df['BB_Lower'] = bollinger.bollinger_lband() 

    #     # --- Average True Range (ATR) ---
    #     if atr:
    #         atr = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    #         df['ATR'] = atr.average_true_range()
            
    #     df['Date'] = df.index
        
    #     return df
    
    @staticmethod
    def get_ma_context(df: pd.DataFrame, decimal_places: int, period: int = 20) -> str:
        df = df.copy()

        df['EMA20_cross_above_EMA50'] = (df['EMA20'] > df['EMA50']) & (df['EMA20'].shift(1) <= df['EMA50'].shift(1))
        df['EMA20_cross_below_EMA50'] = (df['EMA20'] < df['EMA50']) & (df['EMA20'].shift(1) >= df['EMA50'].shift(1))

        # Similarly, you can detect crossovers between other EMAs
        df['EMA50_cross_above_EMA100'] = (df['EMA50'] > df['EMA100']) & (df['EMA50'].shift(1) <= df['EMA100'].shift(1))
        df['EMA50_cross_below_EMA100'] = (df['EMA50'] < df['EMA100']) & (df['EMA50'].shift(1) >= df['EMA100'].shift(1))

        # Detect when the Close price crosses above or below EMA20
        df['Price_cross_above_EMA20'] = (df['Close'] > df['EMA20']) & (df['Close'].shift(1) <= df['EMA20'].shift(1))
        df['Price_cross_below_EMA20'] = (df['Close'] < df['EMA20']) & (df['Close'].shift(1) >= df['EMA20'].shift(1))

        # Detect when the Close price crosses above or below EMA50
        df['Price_cross_above_EMA50'] = (df['Close'] > df['EMA50']) & (df['Close'].shift(1) <= df['EMA50'].shift(1))
        df['Price_cross_below_EMA50'] = (df['Close'] < df['EMA50']) & (df['Close'].shift(1) >= df['EMA50'].shift(1))

        # Detect when the Close price crosses above or below EMA100
        df['Price_cross_above_EMA100'] = (df['Close'] > df['EMA100']) & (df['Close'].shift(1) <= df['EMA100'].shift(1))
        df['Price_cross_below_EMA100'] = (df['Close'] < df['EMA100']) & (df['Close'].shift(1) >= df['EMA100'].shift(1))

        # Create a list to store our natural language events
        events = [f"In the last {period} bars: "]

        for idx, row in df[period * -1:].iterrows():
            date = row['Date']
            if row['EMA20_cross_above_EMA50']:
                events.append(f"On {date}, EMA20 crossed above EMA50.")
            if row['EMA20_cross_below_EMA50']:
                events.append(f"On {date}, EMA20 crossed below EMA50.")
            if row['EMA50_cross_above_EMA100']:
                events.append(f"On {date}, EMA50 crossed above EMA100.")
            if row['EMA50_cross_below_EMA100']:
                events.append(f"On {date}, EMA50 crossed below EMA100.")
            if row['Price_cross_above_EMA20']:
                events.append(f"On {date}, the closing price crossed above EMA20.")
            if row['Price_cross_below_EMA20']:
                events.append(f"On {date}, the closing price crossed below EMA20.")
            if row['Price_cross_above_EMA50']:	
                events.append(f"On {date}, the closing price crossed above EMA50.")
            if row['Price_cross_below_EMA50']:
                events.append(f"On {date}, the closing price crossed below EMA50.")
            if row['Price_cross_above_EMA100']:
                events.append(f"On {date}, the closing price crossed above EMA100.")
            if row['Price_cross_below_EMA100']:
                events.append(f"On {date}, the closing price crossed below EMA100.")
        
        cross_over_context = "\n".join(events) if events else "No significant crossover events detected."

        last_bar = df.iloc[-1]
        values = {
            'EMA20': last_bar['EMA20'].round(decimal_places),
            'EMA50': last_bar['EMA50'].round(decimal_places),
            'EMA100': last_bar['EMA100'].round(decimal_places),
            'Close': last_bar['Close'].round(decimal_places),
        }
        sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)
        price_context = " > ".join([f"{k}: {v}" for k, v in sorted_items])

        return f"{cross_over_context}\nLatest Values in descending order:\n**{price_context}**"
    
    @staticmethod
    def get_macd_context(df: pd.DataFrame, decimal_places: int, period: int = 20) -> str:
        # Create a copy of the dataframe
        df = df.copy()
        
        # Detect when the MACD line crosses above or below the MACD Signal line
        df['MACD_cross_above_Signal'] = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
        df['MACD_cross_below_Signal'] = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))
        
        # Detect when the MACD histogram (MACD_Diff) crosses zero
        df['MACD_Diff_cross_above_0'] = (df['MACD_Diff'] > 0) & (df['MACD_Diff'].shift(1) <= 0)
        df['MACD_Diff_cross_below_0'] = (df['MACD_Diff'] < 0) & (df['MACD_Diff'].shift(1) >= 0)
        
        # List to store natural language events for the most recent period
        events = [f"In the last {period} bars: "]
        
        # Iterate over the last 20 rows of the dataframe
        for idx, row in df[period * -1:].iterrows():
            date = row['Date']
            if row['MACD_cross_above_Signal']:
                events.append(f"On {date}, MACD crossed above the MACD Signal line.")
            if row['MACD_cross_below_Signal']:
                events.append(f"On {date}, MACD crossed below the MACD Signal line.")
            if row['MACD_Diff_cross_above_0']:
                events.append(f"On {date}, the MACD histogram turned positive (MACD_Diff crossed above 0).")
            if row['MACD_Diff_cross_below_0']:
                events.append(f"On {date}, the MACD histogram turned negative (MACD_Diff crossed below 0).")
        
        # Build the context string for MACD events
        macd_context = "\n".join(events) if events else "No significant MACD events detected."
        
        # Summarize the latest indicator values, rounding them appropriately.
        last_bar = df.iloc[-1]

        values_context = f"MACD: {last_bar['MACD'].round(decimal_places)}, MACD Signal: {last_bar['MACD_Signal'].round(decimal_places)}, MACD Diff: {last_bar['MACD_Diff'].round(decimal_places)}"
        
        # Return the final natural language description with the events and the latest sorted values.
        return f"{macd_context}\nLatest Values:\n**{values_context}**"

    @staticmethod
    def get_atr_context(df: pd.DataFrame, decimal_places: int) -> str:
        # Create a copy of the dataframe
        df = df.copy()
        
        # Get the latest ATR value
        last_atr = df['ATR'].iloc[-1].round(decimal_places)
        
        # Get the latest closing price
        last_close = df['Close'].iloc[-1].round(decimal_places)
        
        # Calculate the ATR context
        atr_context = f"Latest ATR: {last_atr}, Latest Close: {last_close}"
        
        return atr_context
    
    @staticmethod
    def get_rsi_context(df: pd.DataFrame, decimal_places: int) -> str:
        # Create a copy of the dataframe
        df = df.copy()
        
        # Get the latest RSI value
        last_rsi = df['RSI14'].iloc[-1].round(decimal_places)
        
        # Determine the RSI context based on the latest value
        if last_rsi > 70:
            rsi_context = "Overbought"
        elif last_rsi < 30:
            rsi_context = "Oversold"
        else:
            rsi_context = "Neutral"
        
        return f"Latest RSI: {last_rsi}"