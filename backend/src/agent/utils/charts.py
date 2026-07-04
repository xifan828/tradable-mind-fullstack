import matplotlib
matplotlib.use('Agg')
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MaxNLocator
from matplotlib import pyplot as plt
from mplfinance.original_flavor import candlestick_ohlc
import pandas as pd
import os
import re
import numpy as np
import math
import base64
import io
from agent.utils.constants import get_decimal_places

class TechnicalCharts:
    def __init__(self, symbol: str, interval: str, df: pd.DataFrame, size: int, chart_name: str):
        self.symbol = symbol
        self.interval = interval
        self.df = df
        self.size = size
        self.chart_name = chart_name
        self.chart_root_path = "data/chart"

    @staticmethod
    def _sanitize_chart_name(name: str) -> str:
        """Remove characters invalid for file names on most OSes."""
        sanitized = re.sub(r"[\\/:*?\"<>|]+", "_", name.strip())
        return sanitized or "chart"
    
    @staticmethod
    def _compute_pip_interval(y_min: float, y_max: float, decimal_places: int, max_ticks: int = 10) -> float:
        """Derive a "nice" tick interval so we draw at most `max_ticks` labels."""
        min_step = 10 ** (-decimal_places)
        span = max(y_max - y_min, min_step)
        target_interval = span / max(max_ticks - 1, 1)
        if not math.isfinite(target_interval) or target_interval <= 0:
            target_interval = min_step

        exponent = math.floor(math.log10(target_interval)) if target_interval > 0 else 0
        base = 10 ** exponent
        for multiplier in (1, 2, 5):
            candidate = multiplier * base
            if target_interval <= candidate:
                interval = candidate
                break
        else:
            interval = 10 * base

        interval = max(interval, min_step)
        step_count = max(1, math.ceil(interval / min_step))
        return step_count * min_step
    
    def plot_chart(self,
               EMA10: bool = False,
               EMA20: bool = False,
               EMA50: bool = False,
               EMA100: bool = False,
               RSI14: bool = False,
               MACD: bool = False,
               ROC12: bool = False,
               ATR14: bool = False,
               BB: bool = False,
               pivot_levels: dict = None,
               fibonacci_levels: dict = None,
               shading: bool = False):
        # collect current data
        # NOTE: `return_binary` retained for backward compatibility; output is always base64.
        data = {}
        decimal_places = get_decimal_places(self.symbol)

        # --- Data Preparation ---
        ohlc_df = self.df.copy()
        ohlc_df = ohlc_df.tail(self.size)
        data["Close"] = ohlc_df.iloc[-1]["Close"].round(decimal_places)

        # Create a new sequential index column
        ohlc_df.loc[:, 'Index'] = range(len(ohlc_df))
        ohlc_data = ohlc_df[['Index', 'Open', 'High', 'Low', 'Close']].copy()

        # --- Define the Indicator Settings from Input Parameters ---
        indicators = {
            'EMA10': EMA10,
            'EMA20': EMA20,
            'EMA50': EMA50,
            'EMA100': EMA100,
            'RSI14': RSI14,
            'MACD': MACD,
            'ROC12': ROC12,
            'ATR14': ATR14,
            'BB': BB,
        }

        # Determine which additional subplots to create.
        additional_indicators = []
        if indicators.get('RSI14'):
            additional_indicators.append('RSI')
        if indicators.get('MACD'):
            additional_indicators.append('MACD')
        if indicators.get('ROC12'):
            additional_indicators.append('ROC')
        if indicators.get('ATR14'):
            additional_indicators.append('ATR')

        # --- Figure Setup: Dynamic Subplots ---
        # Fixed size for the candlestick chart and each additional indicator chart
        price_chart_height_inch = 10      # Fixed height for the price chart
        indicator_height_inch = 3         # Fixed height for each additional indicator
        total_height = price_chart_height_inch + indicator_height_inch * len(additional_indicators)
        n_subplots = 1 + len(additional_indicators)
        height_ratios = [price_chart_height_inch] + [indicator_height_inch] * len(additional_indicators)

        fig, axes = plt.subplots(nrows=n_subplots, figsize=(20, total_height),
                                gridspec_kw={'height_ratios': height_ratios}, sharex=False)
        if n_subplots == 1:
            axes = [axes]
        ax_price = axes[0]

        # Map additional indicators to their dedicated axes in order (top to bottom)
        indicator_axes = {}
        for i, indicator in enumerate(additional_indicators):
            indicator_axes[indicator] = axes[i + 1]

        # --- Plot 1: Price Chart (Candlestick with Optional EMA Lines) ---
        lines = []
        labels = []
        candlestick_ohlc(ax_price, ohlc_data.values, width=0.6, colorup='green', colordown='red', alpha=0.8)
        # adjust wick width
        for line in ax_price.get_lines():
            x_data = line.get_xdata()
            # Check if the line is vertical (both x values are the same)
            if len(x_data) == 2 and x_data[0] == x_data[1]:
                line.set_linewidth(2.5) 

        if indicators.get('EMA10'):
            line, = ax_price.plot(ohlc_df['Index'], ohlc_df['EMA10'], label='EMA 10', color='blue', linewidth=2)
            lines.append(line)
            labels.append("EMA 10: blue")
            data["EMA10"] = ohlc_df.iloc[-1]["EMA10"].round(decimal_places)
        if indicators.get('EMA20'):
            line, = ax_price.plot(ohlc_df['Index'], ohlc_df['EMA20'], label='EMA 20', color='orange', linewidth=2)
            lines.append(line)
            labels.append("EMA 20: orange")
            data["EMA20"] = ohlc_df.iloc[-1]["EMA20"].round(decimal_places)
        if indicators.get('EMA50'):
            line, = ax_price.plot(ohlc_df['Index'], ohlc_df['EMA50'], label='EMA 50', color='purple', linewidth=2)
            lines.append(line)
            labels.append("EMA 50: purple")
            data["EMA50"] = ohlc_df.iloc[-1]["EMA50"].round(decimal_places)
        if indicators.get('EMA100'):
            line, = ax_price.plot(ohlc_df['Index'], ohlc_df['EMA100'], label='EMA 100', color='violet', linewidth=2)
            lines.append(line)
            labels.append("EMA 100: violet")
            data["EMA100"] = ohlc_df.iloc[-1]["EMA100"].round(decimal_places)
        # Bollinger Bands
        if indicators.get('BB'):
            ax_price.plot(ohlc_df['Index'], ohlc_df['BB_Upper'], label='BB Upper', color='gray', linewidth=1.5, linestyle='--')
            ax_price.plot(ohlc_df['Index'], ohlc_df['BB_Middle'], label='BB Middle', color='blue', linewidth=1.5)
            ax_price.plot(ohlc_df['Index'], ohlc_df['BB_Lower'], label='BB Lower', color='gray', linewidth=1.5, linestyle='--')
            ax_price.fill_between(ohlc_df['Index'], ohlc_df['BB_Upper'], ohlc_df['BB_Lower'], alpha=0.15, color='blue')
            lines.append(ax_price.plot([], [], color='blue', linewidth=1.5)[0])
            labels.append("BB Middle: blue")
            lines.append(ax_price.plot([], [], color='gray', linewidth=1.5, linestyle='--')[0])
            labels.append("BB Upper/Lower: gray")
            data["BB_Upper"] = ohlc_df.iloc[-1]["BB_Upper"].round(decimal_places)
            data["BB_Middle"] = ohlc_df.iloc[-1]["BB_Middle"].round(decimal_places)
            data["BB_Lower"] = ohlc_df.iloc[-1]["BB_Lower"].round(decimal_places)
        # Pivot Points
        if pivot_levels:
            pivot_colors = {
                'Pivot': 'blue',
                'R1': 'red', 'R2': 'red', 'R3': 'red',
                'S1': 'green', 'S2': 'green', 'S3': 'green',
            }
            pivot_styles = {
                'Pivot': '-',
                'R1': '--', 'R2': '-.', 'R3': ':',
                'S1': '--', 'S2': '-.', 'S3': ':',
            }
            for level_name, level_value in pivot_levels.items():
                color = pivot_colors.get(level_name, 'gray')
                style = pivot_styles.get(level_name, '--')
                ax_price.axhline(y=level_value, color=color, linestyle=style, linewidth=1.2, alpha=0.8)
                ax_price.text(len(ohlc_df) + 0.5, level_value, f'{level_name}: {level_value:.{decimal_places}f}',
                             va='center', ha='left', fontsize=9, color=color)
            data["pivot_levels"] = pivot_levels
        # Fibonacci Levels
        if fibonacci_levels:
            fib_colors = {
                'fib_0': 'gray', 'fib_236': 'purple', 'fib_382': 'blue',
                'fib_500': 'green', 'fib_618': 'orange', 'fib_786': 'red', 'fib_1': 'gray',
            }
            fib_labels = {
                'fib_0': '0%', 'fib_236': '23.6%', 'fib_382': '38.2%',
                'fib_500': '50%', 'fib_618': '61.8%', 'fib_786': '78.6%', 'fib_1': '100%',
            }
            for level_name, level_value in fibonacci_levels.items():
                color = fib_colors.get(level_name, 'gray')
                label = fib_labels.get(level_name, level_name)
                ax_price.axhline(y=level_value, color=color, linestyle='--', linewidth=1.2, alpha=0.7)
                ax_price.text(len(ohlc_df) + 0.5, level_value, f'{label}: {level_value:.{decimal_places}f}',
                             va='center', ha='left', fontsize=9, color=color)
            data["fibonacci_levels"] = fibonacci_levels
        if lines:
            ax_price.legend(lines, labels, loc='upper left', fontsize=12)
        ax_price.set_title(f"{self.symbol}")
        ax_price.grid(True)

        # --- Plot Additional Indicators ---
        # RSI Plot
        if 'RSI' in indicator_axes:
            ax_rsi = indicator_axes['RSI']
            ax_rsi.plot(ohlc_df['Index'], ohlc_df['RSI14'], label='RSI (14)', color='purple')
            ax_rsi.axhline(70, color='red', linestyle='--')
            ax_rsi.axhline(30, color='green', linestyle='--')
            ax_rsi.legend(loc='upper left')
            ax_rsi.grid(True)
            data["RSI14"] = ohlc_df.iloc[-1]["RSI14"].round(2)
        # MACD Plot
        if 'MACD' in indicator_axes:
            ax_macd = indicator_axes['MACD']
            lines = []
            labels = []
            line, = ax_macd.plot(ohlc_df['Index'], ohlc_df['MACD'], label='MACD', color='red')
            lines.append(line)
            labels.append("MACD: red")
            line, = ax_macd.plot(ohlc_df['Index'], ohlc_df['MACD_Signal'], label='Signal', color='green')
            lines.append(line)
            labels.append("Signal: green")
            macd_diff = ohlc_df['MACD_Diff']
            pos_diff = macd_diff.copy()
            neg_diff = macd_diff.copy()
            pos_diff[pos_diff <= 0] = 0  # Only positive values
            neg_diff[neg_diff >= 0] = 0  # Only negative values
            ax_macd.bar(ohlc_df['Index'], pos_diff, color='peru', label='Divergence', width=0.6)
            ax_macd.bar(ohlc_df['Index'], neg_diff, color='black', width=0.6)
            ax_macd.legend(lines, labels, loc='upper left', fontsize=12)
            ax_macd.grid(True)
            data["MACD"] = ohlc_df.iloc[-1]["MACD"].round(decimal_places)
            data["MACD_Signal"] = ohlc_df.iloc[-1]["MACD_Signal"].round(decimal_places)
            data["MACD_Diff"] = ohlc_df.iloc[-1]["MACD_Diff"].round(decimal_places)
        # ROC Plot
        if 'ROC' in indicator_axes:
            ax_roc = indicator_axes['ROC']
            ax_roc.plot(ohlc_df['Index'], ohlc_df['ROC12'], label='ROC (12)', color='green')
            ax_roc.axhline(0, color='black', linestyle='--')
            ax_roc.legend(loc='upper left')
            ax_roc.grid(True)
            data["ROC12"] = ohlc_df.iloc[-1]["ROC12"].round(2)
        # ATR Plot
        if 'ATR' in indicator_axes:
            ax_atr = indicator_axes['ATR']
            ax_atr.plot(ohlc_df['Index'], ohlc_df['ATR'], label='ATR (14)', color='blue')
            ax_atr.legend(loc='upper left')
            ax_atr.grid(True)
            data["ATR14"] = ohlc_df.iloc[-1]["ATR"].round(decimal_places)

        # --- Formatting: Axis Labels, Ticks, and Grids ---
        def make_price_formatter(decimal_places):
            def price_formatter(x, pos):
                return f"{x:.{decimal_places}f}"
            return price_formatter
        formatter = make_price_formatter(decimal_places)

        # Calculate y-axis limits based on OHLC data only (ignore pivot/fibonacci levels)
        raw_y_min = ohlc_df['Low'].min()
        raw_y_max = ohlc_df['High'].max()
        # Add small padding (2% of range) for visual comfort
        y_padding = (raw_y_max - raw_y_min) * 0.02
        raw_y_min -= y_padding
        raw_y_max += y_padding
        max_ticks = 10
        pip_interval = self._compute_pip_interval(raw_y_min, raw_y_max, decimal_places, max_ticks=max_ticks)

        def _align_bounds(interval: float):
            min_aligned = math.floor(raw_y_min / interval) * interval
            max_aligned = math.ceil(raw_y_max / interval) * interval
            return min_aligned, max_aligned

        y_min, y_max = _align_bounds(pip_interval)
        tick_count = int(round((y_max - y_min) / pip_interval)) + 1
        guard = 0
        while tick_count > max_ticks and guard < 6:
            pip_interval *= 2
            y_min, y_max = _align_bounds(pip_interval)
            tick_count = int(round((y_max - y_min) / pip_interval)) + 1
            guard += 1

        y_ticks = np.arange(y_min, y_max + (pip_interval / 2), pip_interval)
        # num_ticks = int(round((y_max - y_min) / pip_interval)) + 1
        # y_ticks = np.linspace(y_min, y_max, num_ticks)

        def date_formatter(x, pos):
            index = int(round(x))
            if index < len(ohlc_df):
                return ohlc_df['Date'].iloc[index].strftime('%m-%d %H:%M')
            return ''

        # Combine all axes (price chart + additional) for common formatting.
        all_axes = [ax_price] + [indicator_axes[ind] for ind in additional_indicators]
        for i, ax in enumerate(all_axes):
            ax.xaxis.set_major_formatter(FuncFormatter(date_formatter))
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, prune='both', nbins=20))
            ax.set_xlim(-1, len(ohlc_df) + 1)
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
            if i == 0:
                ax.yaxis.set_major_formatter(FuncFormatter(formatter))
                ax.set_yticks(y_ticks)
                ax.set_ylim(y_min, y_max)  # Explicitly set limits to exclude pivot/fib levels
                ax.tick_params(axis='x', rotation=0)
            else:
                ax.set_xticklabels([])
                ax.tick_params(axis='x', length=0)
            ax.grid(True, alpha=0.4)

        # --- Shading ---
        if shading:
            time_intervals_dict = {"5min": 0, "15min": 0, "1h": 6, "4h": 5}
            bars_to_mark = time_intervals_dict[self.interval]
            start_shade = max(0, len(ohlc_df) - bars_to_mark)
            end_shade = len(ohlc_df)
            for ax in all_axes:
                ax.axvspan(start_shade, end_shade, facecolor='blue', alpha=0.2, zorder=-1)

        # Save and close the figure
        plt.tight_layout()

        os.makedirs(self.chart_root_path, exist_ok=True)
        safe_name = self._sanitize_chart_name(self.chart_name)
        chart_path = os.path.join(self.chart_root_path, f"{safe_name}.png")

        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        chart_bytes = buf.getvalue()
        encoded_chart = base64.b64encode(chart_bytes).decode('utf-8')
        with open(chart_path, 'wb') as chart_file:
            chart_file.write(chart_bytes)
        buf.close()

        plt.close(fig)
        return data, encoded_chart