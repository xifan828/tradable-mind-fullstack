"""
Scenario Analysis: Monday Weekly Extreme Hypothesis

Hypothesis: In what percentage of weeks does the High or the Low established
on Monday (00:00–23:59 UTC) remain the High or the Low for the entire trading week?

This tests whether Monday tends to set one of the week's extremes.
"""

import pandas as pd
from pathlib import Path


def load_data(filepath: str) -> pd.DataFrame:
    """Load and prepare the CSV data."""
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    df['day_of_week'] = df['datetime'].dt.dayofweek  # 0=Monday, 4=Friday
    df['year'] = df['datetime'].dt.isocalendar().year
    df['week'] = df['datetime'].dt.isocalendar().week
    df['year_week'] = df['year'].astype(str) + '-W' + df['week'].astype(str).str.zfill(2)
    return df


def analyze_week(week_df: pd.DataFrame) -> dict | None:
    """
    Analyze a single trading week.

    Returns None if the week doesn't have Monday data or is incomplete.
    Returns dict with analysis results.
    """
    # Filter for Monday (day_of_week = 0)
    monday_df = week_df[week_df['day_of_week'] == 0]

    if monday_df.empty:
        return None

    # Get weekdays only (Mon-Fri, day_of_week 0-4)
    weekdays_df = week_df[week_df['day_of_week'] <= 4]

    if weekdays_df.empty:
        return None

    # Need at least 3 trading days for a valid week
    unique_days = weekdays_df['day_of_week'].nunique()
    if unique_days < 3:
        return None

    # Monday's High and Low
    monday_high = monday_df['High'].max()
    monday_low = monday_df['Low'].min()

    # Week's High and Low (Mon-Fri)
    week_high = weekdays_df['High'].max()
    week_low = weekdays_df['Low'].min()

    # Check if Monday set the weekly extreme
    monday_is_week_high = monday_high == week_high
    monday_is_week_low = monday_low == week_low
    monday_set_extreme = monday_is_week_high or monday_is_week_low

    return {
        'year_week': week_df['year_week'].iloc[0],
        'monday_date': monday_df['date'].iloc[0],
        'monday_high': monday_high,
        'monday_low': monday_low,
        'monday_range': monday_high - monday_low,
        'week_high': week_high,
        'week_low': week_low,
        'week_range': week_high - week_low,
        'monday_is_week_high': monday_is_week_high,
        'monday_is_week_low': monday_is_week_low,
        'monday_set_extreme': monday_set_extreme,
        'trading_days': unique_days,
    }


def find_all_weeks(df: pd.DataFrame) -> list[dict]:
    """Analyze all weeks in the dataset."""
    results = []

    for year_week, week_df in df.groupby('year_week'):
        result = analyze_week(week_df)
        if result is not None:
            results.append(result)

    # Sort by date
    results.sort(key=lambda x: x['monday_date'])
    return results


def analyze_results(results: list[dict], label: str = "") -> dict:
    """Analyze the hypothesis results."""
    if not results:
        return {'error': 'No valid weeks found'}

    total = len(results)

    # Count occurrences
    high_count = sum(1 for r in results if r['monday_is_week_high'])
    low_count = sum(1 for r in results if r['monday_is_week_low'])
    either_count = sum(1 for r in results if r['monday_set_extreme'])
    both_count = sum(1 for r in results if r['monday_is_week_high'] and r['monday_is_week_low'])

    return {
        'label': label,
        'total_weeks': total,
        'monday_is_week_high': high_count,
        'monday_is_week_low': low_count,
        'monday_set_either': either_count,
        'monday_set_both': both_count,
        'pct_high': high_count / total * 100,
        'pct_low': low_count / total * 100,
        'pct_either': either_count / total * 100,
        'pct_both': both_count / total * 100,
        'date_range': f"{results[0]['monday_date']} to {results[-1]['monday_date']}",
    }


def print_analysis(analysis: dict):
    """Print analysis results in a formatted way."""
    print(f"\n{'='*60}")
    print(f"{analysis['label']}")
    print(f"{'='*60}")
    print(f"Date range: {analysis['date_range']}")
    print(f"Total weeks analyzed: {analysis['total_weeks']}")
    print(f"\n{'Metric':<35} {'Count':>8} {'Percent':>10}")
    print("-" * 55)
    print(f"{'Monday = Week High':<35} {analysis['monday_is_week_high']:>8} {analysis['pct_high']:>9.1f}%")
    print(f"{'Monday = Week Low':<35} {analysis['monday_is_week_low']:>8} {analysis['pct_low']:>9.1f}%")
    print(f"{'Monday = Either (High OR Low)':<35} {analysis['monday_set_either']:>8} {analysis['pct_either']:>9.1f}%")
    print(f"{'Monday = Both (High AND Low)':<35} {analysis['monday_set_both']:>8} {analysis['pct_both']:>9.1f}%")


def main():
    data_path = Path(__file__).parent.parent.parent.parent / 'data' / 'time_series' / 'EUR_USD_1h.csv'

    print("=" * 70)
    print("Monday Weekly Extreme Hypothesis Analysis")
    print("=" * 70)
    print("\nHypothesis:")
    print("  In what percentage of weeks does the High or the Low established")
    print("  on Monday (00:00–23:59 UTC) remain the High or Low for the entire week?")
    print("-" * 70)

    df = load_data(data_path)
    print(f"\nLoaded {len(df)} hourly records")
    print(f"Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}")

    all_results = find_all_weeks(df)
    print(f"Total valid weeks: {len(all_results)}")

    if not all_results:
        print("No valid weeks found!")
        return

    # Analyze full period
    full_analysis = analyze_results(all_results, "FULL PERIOD ANALYSIS")
    print_analysis(full_analysis)

    # Analyze last 50 weeks
    last_50_analysis = None
    if len(all_results) >= 50:
        last_50 = all_results[-50:]
        last_50_analysis = analyze_results(last_50, "LAST 50 WEEKS ANALYSIS")
        print_analysis(last_50_analysis)

    # Analyze last 30 weeks
    last_30_analysis = None
    if len(all_results) >= 30:
        last_30 = all_results[-30:]
        last_30_analysis = analyze_results(last_30, "LAST 30 WEEKS ANALYSIS")
        print_analysis(last_30_analysis)

    # Comparison
    print(f"\n{'='*80}")
    print("COMPARISON: Full Period vs Last 50 Weeks vs Last 30 Weeks")
    print("=" * 80)
    print(f"{'Metric':<25} {'Full Period':>14} {'Last 50 Wks':>14} {'Last 30 Wks':>14}")
    print("-" * 80)

    if last_50_analysis and last_30_analysis:
        print(f"{'Monday = Week High':<25} {full_analysis['pct_high']:>13.1f}% {last_50_analysis['pct_high']:>13.1f}% {last_30_analysis['pct_high']:>13.1f}%")
        print(f"{'Monday = Week Low':<25} {full_analysis['pct_low']:>13.1f}% {last_50_analysis['pct_low']:>13.1f}% {last_30_analysis['pct_low']:>13.1f}%")
        print(f"{'Monday = Either':<25} {full_analysis['pct_either']:>13.1f}% {last_50_analysis['pct_either']:>13.1f}% {last_30_analysis['pct_either']:>13.1f}%")

    # Conclusion
    print(f"\n{'='*70}")
    print("CONCLUSION")
    print("=" * 70)
    pct = full_analysis['pct_either']
    if pct > 50:
        print(f"Monday sets the week's High or Low in {pct:.1f}% of weeks (full period).")
        print("This is ABOVE random chance (theoretically ~40% for 5 trading days).")
        print("Monday appears to be a significant day for establishing weekly extremes.")
    else:
        print(f"Monday sets the week's High or Low in {pct:.1f}% of weeks (full period).")
        print("This is BELOW 50%, suggesting Monday is not particularly special")
        print("for establishing weekly extremes.")

    # Show sample weeks
    print(f"\n{'='*70}")
    print("SAMPLE WEEKS (last 15)")
    print("=" * 70)
    print(f"{'Week':<12} | {'Mon High':>9} | {'Mon Low':>9} | {'Wk High':>9} | {'Wk Low':>9} | Result")
    print("-" * 70)
    for r in all_results[-15:]:
        if r['monday_is_week_high'] and r['monday_is_week_low']:
            result = "BOTH"
        elif r['monday_is_week_high']:
            result = "HIGH"
        elif r['monday_is_week_low']:
            result = "LOW"
        else:
            result = "-"
        print(f"{str(r['monday_date']):<12} | {r['monday_high']:.5f} | {r['monday_low']:.5f} | {r['week_high']:.5f} | {r['week_low']:.5f} | {result}")


if __name__ == '__main__':
    main()
