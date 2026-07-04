"""
Scenario Analysis: London Session Asian High Breakout Reversal

Hypothesis: If the first two hours of the London Session (08:00 - 10:00 UTC)
break the High of the Asian Session (00:00 - 07:00 UTC), what is the probability
that the price reverses and trades below the Asian Session Midpoint before
the New York Open (13:00 UTC)?

Sessions (UTC):
- Asian Session: 00:00 - 06:59 (hours 0-6, 7 candles)
- London First 2 Hours: 08:00 - 09:59 (hours 8-9, 2 candles)
- Observation Window (after breakout, before NY Open): 10:00 - 12:59 (hours 10-12)
- NY Open: 13:00

Note: Each row's datetime is the STARTING time of that hourly candle.
"""

import pandas as pd
from pathlib import Path


def load_data(filepath: str) -> pd.DataFrame:
    """Load and prepare the CSV data."""
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    return df


def analyze_day(day_df: pd.DataFrame) -> dict | None:
    """
    Analyze a single trading day for the hypothesis.

    Returns None if the day doesn't have required data or condition not met.
    Returns dict with analysis if London breaks Asian High.
    """
    # Get candles by hour
    hours = {row['hour']: row for _, row in day_df.iterrows()}

    # Asian Session: hours 0-6 (00:00 to 06:59)
    asian_hours = [0, 1, 2, 3, 4, 5, 6]
    if not all(h in hours for h in asian_hours):
        return None

    # London first 2 hours: hours 8-9 (08:00 to 09:59)
    london_hours = [8, 9]
    if not all(h in hours for h in london_hours):
        return None

    # Hours before NY Open: 10, 11, 12 (10:00 to 12:59)
    pre_ny_hours = [10, 11, 12]
    if not all(h in hours for h in pre_ny_hours):
        return None

    # Calculate Asian Session High and Low
    asian_high = max(hours[h]['High'] for h in asian_hours)
    asian_low = min(hours[h]['Low'] for h in asian_hours)
    asian_midpoint = (asian_high + asian_low) / 2

    # Check if London first 2 hours break Asian High
    london_high = max(hours[h]['High'] for h in london_hours)
    breakout_occurred = london_high > asian_high

    if not breakout_occurred:
        return None

    # Breakout occurred - now check if price reverses below Asian Midpoint
    # Check all candles from 10:00 to 12:59
    reversed_below_midpoint = False
    reversal_hour = None
    reversal_low = None

    for h in pre_ny_hours:
        candle = hours[h]
        if candle['Low'] < asian_midpoint:
            reversed_below_midpoint = True
            reversal_hour = h
            reversal_low = candle['Low']
            break

    return {
        'date': day_df['date'].iloc[0],
        'asian_high': asian_high,
        'asian_low': asian_low,
        'asian_midpoint': asian_midpoint,
        'asian_range': asian_high - asian_low,
        'london_high': london_high,
        'breakout_pips': (london_high - asian_high) * 10000,  # For EUR/USD
        'reversed_below_midpoint': reversed_below_midpoint,
        'reversal_hour': reversal_hour,
        'reversal_low': reversal_low,
    }


def find_breakout_days(df: pd.DataFrame) -> list[dict]:
    """Find all days where London broke Asian High."""
    results = []

    for date, day_df in df.groupby('date'):
        result = analyze_day(day_df)
        if result is not None:
            results.append(result)

    return results


def analyze_results(results: list[dict]) -> dict:
    """Analyze the hypothesis results."""
    if not results:
        return {'error': 'No breakout days found'}

    total = len(results)
    reversed_count = sum(1 for r in results if r['reversed_below_midpoint'])
    not_reversed = total - reversed_count

    breakout_pips = [r['breakout_pips'] for r in results]
    asian_ranges = [r['asian_range'] * 10000 for r in results]  # Convert to pips

    return {
        'total_breakout_days': total,
        'reversed_to_midpoint': reversed_count,
        'did_not_reverse': not_reversed,
        'reversal_probability_pct': reversed_count / total * 100,
        'avg_breakout_pips': sum(breakout_pips) / len(breakout_pips),
        'avg_asian_range_pips': sum(asian_ranges) / len(asian_ranges),
        'min_breakout_pips': min(breakout_pips),
        'max_breakout_pips': max(breakout_pips),
    }


def main(limit: int = None):
    data_path = Path(__file__).parent.parent.parent.parent / 'data' / 'time_series' / 'EUR_USD_1h.csv'

    print("=" * 70)
    print("London Session Asian High Breakout Reversal Analysis")
    if limit:
        print(f"(Analyzing latest {limit} occurrences)")
    print("=" * 70)
    print("\nHypothesis:")
    print("  If London first 2 hours (08:00-10:00 UTC) break the Asian High,")
    print("  what is the probability that price reverses and trades below")
    print("  the Asian Midpoint before NY Open (13:00 UTC)?")
    print("\nSession Definitions (UTC):")
    print("  - Asian Session: 00:00 - 06:59 (hours 0-6)")
    print("  - London First 2h: 08:00 - 09:59 (hours 8-9)")
    print("  - Pre-NY Window: 10:00 - 12:59 (hours 10-12)")
    print("-" * 70)

    df = load_data(data_path)
    print(f"\nLoaded {len(df)} hourly records")
    print(f"Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}")

    # Count unique days
    unique_days = df['date'].nunique()
    print(f"Total trading days: {unique_days}")

    all_results = find_breakout_days(df)
    print(f"\nFound {len(all_results)} total days where London broke Asian High")

    # Apply limit to get latest N occurrences
    if limit and len(all_results) > limit:
        results = all_results[-limit:]  # Take latest N (sorted by date)
        print(f"Analyzing latest {limit} occurrences ({results[0]['date']} to {results[-1]['date']})")
    else:
        results = all_results

    if not results:
        print("No breakout days found!")
        return

    analysis = analyze_results(results)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total days with Asian High breakout:  {analysis['total_breakout_days']}")
    print(f"Price reversed to Asian Midpoint:     {analysis['reversed_to_midpoint']} ({analysis['reversal_probability_pct']:.1f}%)")
    print(f"Price did NOT reverse to Midpoint:    {analysis['did_not_reverse']} ({100 - analysis['reversal_probability_pct']:.1f}%)")
    print(f"\nBreakout Statistics (pips):")
    print(f"  Average breakout above Asian High: {analysis['avg_breakout_pips']:.1f} pips")
    print(f"  Min breakout: {analysis['min_breakout_pips']:.1f} pips")
    print(f"  Max breakout: {analysis['max_breakout_pips']:.1f} pips")
    print(f"\nAsian Session Range:")
    print(f"  Average: {analysis['avg_asian_range_pips']:.1f} pips")

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    prob = analysis['reversal_probability_pct']
    if prob > 50:
        print(f"Hypothesis SUPPORTED: {prob:.1f}% of breakouts reversed to Asian Midpoint")
        print("This suggests a potential mean-reversion strategy after London breaks Asian High.")
    else:
        print(f"Hypothesis NOT SUPPORTED: Only {prob:.1f}% of breakouts reversed to Midpoint")
        print("This suggests breakouts tend to continue rather than reverse.")

    # Show some examples
    print("\n" + "=" * 70)
    print("SAMPLE BREAKOUT DAYS (first 15)")
    print("=" * 70)
    print(f"{'Date':<12} | {'Asian H':>8} | {'Midpoint':>8} | {'Breakout':>8} | {'Reversed':>8}")
    print("-" * 70)
    for r in results[:15]:
        status = "YES" if r['reversed_below_midpoint'] else "NO"
        reversal_info = f"@{r['reversal_hour']}:00" if r['reversed_below_midpoint'] else ""
        print(f"{str(r['date']):<12} | {r['asian_high']:.5f} | {r['asian_midpoint']:.5f} | {r['breakout_pips']:+7.1f}p | {status:>4} {reversal_info}")


if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=limit)
