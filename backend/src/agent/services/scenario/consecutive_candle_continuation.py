"""
Scenario Analysis: Consecutive Candle Continuation Hypothesis

Question: If EUR/USD closes three consecutive H1 candles in the same direction
(e.g., three consecutive Higher Closes), what is the probability that the 4th
candle will also trade beyond the 3rd candle's High (for bullish) or Low (for bearish)?

Definitions:
- Bullish sequence: Close[1] > Close[0], Close[2] > Close[1], Close[3] > Close[2]
- 4th candle continuation (bullish): High[4] > High[3]
- Bearish sequence: Close[1] < Close[0], Close[2] < Close[1], Close[3] < Close[2]
- 4th candle continuation (bearish): Low[4] < Low[3]
"""

import pandas as pd
from pathlib import Path


def load_data(filepath: str) -> pd.DataFrame:
    """Load and prepare the CSV data."""
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df


def find_sequences(df: pd.DataFrame) -> list[dict]:
    """
    Find all 3-candle consecutive sequences and analyze the 4th candle.

    Returns list of sequence results.
    """
    results = []

    # Need at least 4 candles
    if len(df) < 4:
        return results

    for i in range(len(df) - 3):
        c0 = df.iloc[i]    # First candle
        c1 = df.iloc[i+1]  # Second candle
        c2 = df.iloc[i+2]  # Third candle
        c3 = df.iloc[i+3]  # Fourth candle (the one we check for continuation)

        # Check for bullish sequence (3 consecutive higher closes)
        bullish_seq = (c1['Close'] > c0['Close'] and
                       c2['Close'] > c1['Close'])

        # Check for bearish sequence (3 consecutive lower closes)
        bearish_seq = (c1['Close'] < c0['Close'] and
                       c2['Close'] < c1['Close'])

        if bullish_seq:
            # Check if 4th candle trades beyond 3rd candle's High
            continuation = c3['High'] > c2['High']
            extension_pips = (c3['High'] - c2['High']) * 10000 if continuation else 0

            results.append({
                'datetime': c2['datetime'],
                'sequence_type': 'bullish',
                'c0_close': c0['Close'],
                'c1_close': c1['Close'],
                'c2_close': c2['Close'],
                'c2_high': c2['High'],
                'c3_high': c3['High'],
                'c3_low': c3['Low'],
                'continuation': continuation,
                'extension_pips': extension_pips,
            })

        elif bearish_seq:
            # Check if 4th candle trades beyond 3rd candle's Low
            continuation = c3['Low'] < c2['Low']
            extension_pips = (c2['Low'] - c3['Low']) * 10000 if continuation else 0

            results.append({
                'datetime': c2['datetime'],
                'sequence_type': 'bearish',
                'c0_close': c0['Close'],
                'c1_close': c1['Close'],
                'c2_close': c2['Close'],
                'c2_low': c2['Low'],
                'c3_high': c3['High'],
                'c3_low': c3['Low'],
                'continuation': continuation,
                'extension_pips': extension_pips,
            })

    return results


def analyze_results(results: list[dict], label: str = "") -> dict:
    """Analyze the hypothesis results."""
    if not results:
        return {'error': 'No sequences found'}

    total = len(results)

    # Split by sequence type
    bullish = [r for r in results if r['sequence_type'] == 'bullish']
    bearish = [r for r in results if r['sequence_type'] == 'bearish']

    # Bullish stats
    bullish_total = len(bullish)
    bullish_cont = sum(1 for r in bullish if r['continuation'])
    bullish_pct = (bullish_cont / bullish_total * 100) if bullish_total > 0 else 0
    bullish_ext_pips = [r['extension_pips'] for r in bullish if r['continuation']]
    bullish_avg_ext = sum(bullish_ext_pips) / len(bullish_ext_pips) if bullish_ext_pips else 0

    # Bearish stats
    bearish_total = len(bearish)
    bearish_cont = sum(1 for r in bearish if r['continuation'])
    bearish_pct = (bearish_cont / bearish_total * 100) if bearish_total > 0 else 0
    bearish_ext_pips = [r['extension_pips'] for r in bearish if r['continuation']]
    bearish_avg_ext = sum(bearish_ext_pips) / len(bearish_ext_pips) if bearish_ext_pips else 0

    # Combined stats
    total_cont = bullish_cont + bearish_cont
    combined_pct = total_cont / total * 100 if total > 0 else 0

    # Date range
    first_date = results[0]['datetime'].date() if results else None
    last_date = results[-1]['datetime'].date() if results else None

    return {
        'label': label,
        'total_sequences': total,
        'bullish_total': bullish_total,
        'bullish_continuation': bullish_cont,
        'bullish_pct': bullish_pct,
        'bullish_avg_extension_pips': bullish_avg_ext,
        'bearish_total': bearish_total,
        'bearish_continuation': bearish_cont,
        'bearish_pct': bearish_pct,
        'bearish_avg_extension_pips': bearish_avg_ext,
        'combined_continuation': total_cont,
        'combined_pct': combined_pct,
        'date_range': f"{first_date} to {last_date}" if first_date else "N/A",
    }


def print_analysis(analysis: dict):
    """Print analysis results in a formatted way."""
    print(f"\n{'='*70}")
    print(f"{analysis['label']}")
    print(f"{'='*70}")
    print(f"Date range: {analysis['date_range']}")
    print(f"Total 3-candle sequences found: {analysis['total_sequences']}")

    print(f"\n{'BULLISH SEQUENCES (3 Higher Closes)':-^70}")
    print(f"  Total bullish sequences: {analysis['bullish_total']}")
    print(f"  4th candle broke 3rd High: {analysis['bullish_continuation']} ({analysis['bullish_pct']:.1f}%)")
    print(f"  Avg extension when continued: {analysis['bullish_avg_extension_pips']:.1f} pips")

    print(f"\n{'BEARISH SEQUENCES (3 Lower Closes)':-^70}")
    print(f"  Total bearish sequences: {analysis['bearish_total']}")
    print(f"  4th candle broke 3rd Low: {analysis['bearish_continuation']} ({analysis['bearish_pct']:.1f}%)")
    print(f"  Avg extension when continued: {analysis['bearish_avg_extension_pips']:.1f} pips")

    print(f"\n{'COMBINED':-^70}")
    print(f"  Total continuations: {analysis['combined_continuation']} / {analysis['total_sequences']} ({analysis['combined_pct']:.1f}%)")


def main():
    data_path = Path(__file__).parent.parent.parent.parent / 'data' / 'time_series' / 'EUR_USD_1h.csv'

    print("=" * 80)
    print("Consecutive Candle Continuation Hypothesis Analysis")
    print("=" * 80)
    print("\nQuestion:")
    print("  If EUR/USD closes three consecutive H1 candles in the same direction")
    print("  (e.g., three consecutive Higher Closes), what is the probability that")
    print("  the 4th candle will also trade beyond the 3rd candle's High/Low?")
    print("\nDefinitions:")
    print("  - Bullish: 3 consecutive Higher Closes -> Check if 4th High > 3rd High")
    print("  - Bearish: 3 consecutive Lower Closes -> Check if 4th Low < 3rd Low")
    print("-" * 80)

    df = load_data(data_path)
    print(f"\nLoaded {len(df)} hourly records")
    print(f"Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}")

    all_results = find_sequences(df)
    print(f"Total 3-candle sequences found: {len(all_results)}")

    if not all_results:
        print("No sequences found!")
        return

    # Analyze full period
    full_analysis = analyze_results(all_results, "FULL PERIOD ANALYSIS")
    print_analysis(full_analysis)

    # Analyze last 100 occurrences
    last_100_analysis = None
    if len(all_results) >= 100:
        last_100 = all_results[-100:]
        last_100_analysis = analyze_results(last_100, "LAST 100 OCCURRENCES")
        print_analysis(last_100_analysis)

    # Analyze last 50 occurrences
    last_50_analysis = None
    if len(all_results) >= 50:
        last_50 = all_results[-50:]
        last_50_analysis = analyze_results(last_50, "LAST 50 OCCURRENCES")
        print_analysis(last_50_analysis)

    # Analyze last 30 occurrences
    last_30_analysis = None
    if len(all_results) >= 30:
        last_30 = all_results[-30:]
        last_30_analysis = analyze_results(last_30, "LAST 30 OCCURRENCES")
        print_analysis(last_30_analysis)

    # Comparison table
    print(f"\n{'='*95}")
    print("COMPARISON TABLE")
    print("=" * 95)
    print(f"{'Metric':<30} {'Full Period':>14} {'Last 100':>14} {'Last 50':>14} {'Last 30':>14}")
    print("-" * 95)

    if last_100_analysis and last_50_analysis and last_30_analysis:
        print(f"{'Total Sequences':<30} {full_analysis['total_sequences']:>14} {last_100_analysis['total_sequences']:>14} {last_50_analysis['total_sequences']:>14} {last_30_analysis['total_sequences']:>14}")
        print(f"{'Bullish Continuation %':<30} {full_analysis['bullish_pct']:>13.1f}% {last_100_analysis['bullish_pct']:>13.1f}% {last_50_analysis['bullish_pct']:>13.1f}% {last_30_analysis['bullish_pct']:>13.1f}%")
        print(f"{'Bearish Continuation %':<30} {full_analysis['bearish_pct']:>13.1f}% {last_100_analysis['bearish_pct']:>13.1f}% {last_50_analysis['bearish_pct']:>13.1f}% {last_30_analysis['bearish_pct']:>13.1f}%")
        print(f"{'Combined Continuation %':<30} {full_analysis['combined_pct']:>13.1f}% {last_100_analysis['combined_pct']:>13.1f}% {last_50_analysis['combined_pct']:>13.1f}% {last_30_analysis['combined_pct']:>13.1f}%")

    # Conclusion
    print(f"\n{'='*80}")
    print("CONCLUSION")
    print("=" * 80)
    pct = full_analysis['combined_pct']

    if pct > 60:
        print(f"After 3 consecutive same-direction closes, the 4th candle continues")
        print(f"beyond the 3rd candle's extreme in {pct:.1f}% of cases.")
        print("This is a STRONG continuation pattern - momentum tends to persist.")
    elif pct > 50:
        print(f"After 3 consecutive same-direction closes, the 4th candle continues")
        print(f"beyond the 3rd candle's extreme in {pct:.1f}% of cases.")
        print("There is a MODERATE tendency for momentum to continue.")
    else:
        print(f"After 3 consecutive same-direction closes, the 4th candle continues")
        print(f"beyond the 3rd candle's extreme in only {pct:.1f}% of cases.")
        print("Momentum does NOT reliably persist after 3 consecutive candles.")

    # Show sample sequences
    print(f"\n{'='*80}")
    print("SAMPLE SEQUENCES (last 15)")
    print("=" * 80)
    print(f"{'Datetime':<20} | {'Type':<8} | {'3rd Extreme':>11} | {'4th H/L':>11} | Result")
    print("-" * 80)
    for r in all_results[-15:]:
        if r['sequence_type'] == 'bullish':
            extreme = f"{r['c2_high']:.5f}"
            fourth = f"{r['c3_high']:.5f}"
        else:
            extreme = f"{r.get('c2_low', 0):.5f}"
            fourth = f"{r['c3_low']:.5f}"

        result = "CONT" if r['continuation'] else "STOP"
        ext_info = f"+{r['extension_pips']:.1f}p" if r['continuation'] else ""

        print(f"{str(r['datetime']):<20} | {r['sequence_type']:<8} | {extreme:>11} | {fourth:>11} | {result} {ext_info}")


if __name__ == '__main__':
    main()
