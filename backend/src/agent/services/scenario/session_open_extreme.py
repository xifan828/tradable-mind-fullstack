"""
Scenario Analysis: Session Open Extreme Hypothesis

Question: What is the probability that the High or Low of the entire 24-hour cycle
is established within the first 120 minutes of the London Open (08:00–10:00 UTC)
or the New York Open (13:00–15:00 UTC)?

Session Windows (UTC):
- London Open: 08:00 - 09:59 (hours 8-9, 2 candles)
- New York Open: 13:00 - 14:59 (hours 13-14, 2 candles)

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
    Analyze a single trading day.

    Returns None if the day doesn't have sufficient data.
    Returns dict with analysis results.
    """
    # Session open windows
    london_open_hours = [8, 9]  # 08:00-09:59 UTC
    ny_open_hours = [13, 14]    # 13:00-14:59 UTC
    session_open_hours = london_open_hours + ny_open_hours

    # Get candles by hour
    hours = {row['hour']: row for _, row in day_df.iterrows()}

    # Need at least some hours to analyze
    if len(hours) < 12:  # Need at least half a day
        return None

    # Need data for the session windows
    has_london = any(h in hours for h in london_open_hours)
    has_ny = any(h in hours for h in ny_open_hours)

    if not has_london and not has_ny:
        return None

    # Find daily High and Low
    daily_high = day_df['High'].max()
    daily_low = day_df['Low'].min()

    # Find which hour(s) had the daily High
    high_hours = day_df[day_df['High'] == daily_high]['hour'].tolist()

    # Find which hour(s) had the daily Low
    low_hours = day_df[day_df['Low'] == daily_low]['hour'].tolist()

    # Check if High was in session open windows
    high_in_london = any(h in london_open_hours for h in high_hours)
    high_in_ny = any(h in ny_open_hours for h in high_hours)
    high_in_session_open = high_in_london or high_in_ny

    # Check if Low was in session open windows
    low_in_london = any(h in london_open_hours for h in low_hours)
    low_in_ny = any(h in ny_open_hours for h in low_hours)
    low_in_session_open = low_in_london or low_in_ny

    # Either extreme in session open
    either_in_session_open = high_in_session_open or low_in_session_open

    return {
        'date': day_df['date'].iloc[0],
        'daily_high': daily_high,
        'daily_low': daily_low,
        'daily_range': daily_high - daily_low,
        'high_hour': high_hours[0],  # First occurrence
        'low_hour': low_hours[0],    # First occurrence
        'high_in_london': high_in_london,
        'high_in_ny': high_in_ny,
        'high_in_session_open': high_in_session_open,
        'low_in_london': low_in_london,
        'low_in_ny': low_in_ny,
        'low_in_session_open': low_in_session_open,
        'either_in_session_open': either_in_session_open,
        'hours_available': len(hours),
    }


def find_all_days(df: pd.DataFrame) -> list[dict]:
    """Analyze all trading days in the dataset."""
    results = []

    for date, day_df in df.groupby('date'):
        result = analyze_day(day_df)
        if result is not None:
            results.append(result)

    # Sort by date
    results.sort(key=lambda x: x['date'])
    return results


def analyze_results(results: list[dict], label: str = "") -> dict:
    """Analyze the hypothesis results."""
    if not results:
        return {'error': 'No valid days found'}

    total = len(results)

    # Count occurrences
    high_in_london = sum(1 for r in results if r['high_in_london'])
    high_in_ny = sum(1 for r in results if r['high_in_ny'])
    high_in_session = sum(1 for r in results if r['high_in_session_open'])

    low_in_london = sum(1 for r in results if r['low_in_london'])
    low_in_ny = sum(1 for r in results if r['low_in_ny'])
    low_in_session = sum(1 for r in results if r['low_in_session_open'])

    either_in_session = sum(1 for r in results if r['either_in_session_open'])
    both_in_session = sum(1 for r in results if r['high_in_session_open'] and r['low_in_session_open'])

    return {
        'label': label,
        'total_days': total,
        'high_in_london': high_in_london,
        'high_in_ny': high_in_ny,
        'high_in_session_open': high_in_session,
        'low_in_london': low_in_london,
        'low_in_ny': low_in_ny,
        'low_in_session_open': low_in_session,
        'either_in_session_open': either_in_session,
        'both_in_session_open': both_in_session,
        'pct_high_london': high_in_london / total * 100,
        'pct_high_ny': high_in_ny / total * 100,
        'pct_high_session': high_in_session / total * 100,
        'pct_low_london': low_in_london / total * 100,
        'pct_low_ny': low_in_ny / total * 100,
        'pct_low_session': low_in_session / total * 100,
        'pct_either': either_in_session / total * 100,
        'pct_both': both_in_session / total * 100,
        'date_range': f"{results[0]['date']} to {results[-1]['date']}",
    }


def print_analysis(analysis: dict):
    """Print analysis results in a formatted way."""
    print(f"\n{'='*70}")
    print(f"{analysis['label']}")
    print(f"{'='*70}")
    print(f"Date range: {analysis['date_range']}")
    print(f"Total days analyzed: {analysis['total_days']}")

    print(f"\n{'Metric':<45} {'Count':>8} {'Percent':>10}")
    print("-" * 65)
    print(f"{'HIGH in London Open (08:00-10:00)':<45} {analysis['high_in_london']:>8} {analysis['pct_high_london']:>9.1f}%")
    print(f"{'HIGH in NY Open (13:00-15:00)':<45} {analysis['high_in_ny']:>8} {analysis['pct_high_ny']:>9.1f}%")
    print(f"{'HIGH in Either Session Open':<45} {analysis['high_in_session_open']:>8} {analysis['pct_high_session']:>9.1f}%")
    print("-" * 65)
    print(f"{'LOW in London Open (08:00-10:00)':<45} {analysis['low_in_london']:>8} {analysis['pct_low_london']:>9.1f}%")
    print(f"{'LOW in NY Open (13:00-15:00)':<45} {analysis['low_in_ny']:>8} {analysis['pct_low_ny']:>9.1f}%")
    print(f"{'LOW in Either Session Open':<45} {analysis['low_in_session_open']:>8} {analysis['pct_low_session']:>9.1f}%")
    print("-" * 65)
    print(f"{'EITHER (High OR Low) in Session Opens':<45} {analysis['either_in_session_open']:>8} {analysis['pct_either']:>9.1f}%")
    print(f"{'BOTH (High AND Low) in Session Opens':<45} {analysis['both_in_session_open']:>8} {analysis['pct_both']:>9.1f}%")


def main():
    data_path = Path(__file__).parent.parent.parent.parent / 'data' / 'time_series' / 'EUR_USD_1h.csv'

    print("=" * 80)
    print("Session Open Extreme Hypothesis Analysis")
    print("=" * 80)
    print("\nQuestion:")
    print("  What is the probability that the High or Low of the entire 24-hour cycle")
    print("  is established within the first 120 minutes of the London Open (08:00-10:00 UTC)")
    print("  or the New York Open (13:00-15:00 UTC)?")
    print("\nSession Windows (UTC):")
    print("  - London Open: 08:00 - 09:59 (hours 8-9)")
    print("  - New York Open: 13:00 - 14:59 (hours 13-14)")
    print("-" * 80)

    df = load_data(data_path)
    print(f"\nLoaded {len(df)} hourly records")
    print(f"Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}")

    all_results = find_all_days(df)
    print(f"Total valid days: {len(all_results)}")

    if not all_results:
        print("No valid days found!")
        return

    # Analyze full period
    full_analysis = analyze_results(all_results, "FULL PERIOD ANALYSIS")
    print_analysis(full_analysis)

    # Analyze last 200 days
    last_200_analysis = None
    if len(all_results) >= 200:
        last_200 = all_results[-200:]
        last_200_analysis = analyze_results(last_200, "LAST 200 DAYS ANALYSIS")
        print_analysis(last_200_analysis)

    # Analyze last 100 days
    last_100_analysis = None
    if len(all_results) >= 100:
        last_100 = all_results[-100:]
        last_100_analysis = analyze_results(last_100, "LAST 100 DAYS ANALYSIS")
        print_analysis(last_100_analysis)

    # Comparison table
    print(f"\n{'='*90}")
    print("COMPARISON: Full Period vs Last 200 Days vs Last 100 Days")
    print("=" * 90)
    print(f"{'Metric':<35} {'Full Period':>16} {'Last 200 Days':>16} {'Last 100 Days':>16}")
    print("-" * 90)

    if last_200_analysis and last_100_analysis:
        print(f"{'High in London Open':<35} {full_analysis['pct_high_london']:>15.1f}% {last_200_analysis['pct_high_london']:>15.1f}% {last_100_analysis['pct_high_london']:>15.1f}%")
        print(f"{'High in NY Open':<35} {full_analysis['pct_high_ny']:>15.1f}% {last_200_analysis['pct_high_ny']:>15.1f}% {last_100_analysis['pct_high_ny']:>15.1f}%")
        print(f"{'High in Either Session':<35} {full_analysis['pct_high_session']:>15.1f}% {last_200_analysis['pct_high_session']:>15.1f}% {last_100_analysis['pct_high_session']:>15.1f}%")
        print("-" * 90)
        print(f"{'Low in London Open':<35} {full_analysis['pct_low_london']:>15.1f}% {last_200_analysis['pct_low_london']:>15.1f}% {last_100_analysis['pct_low_london']:>15.1f}%")
        print(f"{'Low in NY Open':<35} {full_analysis['pct_low_ny']:>15.1f}% {last_200_analysis['pct_low_ny']:>15.1f}% {last_100_analysis['pct_low_ny']:>15.1f}%")
        print(f"{'Low in Either Session':<35} {full_analysis['pct_low_session']:>15.1f}% {last_200_analysis['pct_low_session']:>15.1f}% {last_100_analysis['pct_low_session']:>15.1f}%")
        print("-" * 90)
        print(f"{'Either Extreme in Session Opens':<35} {full_analysis['pct_either']:>15.1f}% {last_200_analysis['pct_either']:>15.1f}% {last_100_analysis['pct_either']:>15.1f}%")
        print(f"{'Both Extremes in Session Opens':<35} {full_analysis['pct_both']:>15.1f}% {last_200_analysis['pct_both']:>15.1f}% {last_100_analysis['pct_both']:>15.1f}%")

    # Theoretical baseline
    print(f"\n{'='*80}")
    print("THEORETICAL BASELINE")
    print("=" * 80)
    print("Random chance for High/Low in 4 hours out of 24: ~16.7% each")
    print("Random chance for either High OR Low in 4 hours: ~30.6%")
    print("(This assumes uniform distribution of extremes across hours)")

    # Conclusion
    print(f"\n{'='*80}")
    print("CONCLUSION")
    print("=" * 80)
    pct = full_analysis['pct_either']
    baseline = 30.6  # Theoretical random chance

    if pct > baseline * 1.5:  # 50% above baseline
        print(f"Daily High or Low occurs in Session Opens in {pct:.1f}% of days.")
        print(f"This is SIGNIFICANTLY ABOVE random chance (~{baseline:.1f}%).")
        print("Session Opens (London & NY) are highly significant for establishing daily extremes.")
    elif pct > baseline:
        print(f"Daily High or Low occurs in Session Opens in {pct:.1f}% of days.")
        print(f"This is ABOVE random chance (~{baseline:.1f}%).")
        print("Session Opens show some tendency to establish daily extremes.")
    else:
        print(f"Daily High or Low occurs in Session Opens in {pct:.1f}% of days.")
        print(f"This is NEAR or BELOW random chance (~{baseline:.1f}%).")
        print("Session Opens do not appear special for establishing daily extremes.")

    # Show sample days
    print(f"\n{'='*80}")
    print("SAMPLE DAYS (last 20)")
    print("=" * 80)
    print(f"{'Date':<12} | {'High @':>7} | {'Low @':>7} | {'High in':>10} | {'Low in':>10} | Result")
    print("-" * 80)
    for r in all_results[-20:]:
        high_loc = "London" if r['high_in_london'] else ("NY" if r['high_in_ny'] else "-")
        low_loc = "London" if r['low_in_london'] else ("NY" if r['low_in_ny'] else "-")

        if r['high_in_session_open'] and r['low_in_session_open']:
            result = "BOTH"
        elif r['high_in_session_open']:
            result = "HIGH"
        elif r['low_in_session_open']:
            result = "LOW"
        else:
            result = "-"

        print(f"{str(r['date']):<12} | {r['high_hour']:>5}:00 | {r['low_hour']:>5}:00 | {high_loc:>10} | {low_loc:>10} | {result}")


if __name__ == '__main__':
    main()
