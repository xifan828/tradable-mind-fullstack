"""
Scenario Analysis: Bullish Week Start Hypothesis

Hypothesis: If Monday, Tuesday, and Wednesday are all bullish days
(Tuesday close > Monday close, Wednesday close > Tuesday close),
then Friday will be a loss day (Friday close < Friday open).
"""

import pandas as pd
from pathlib import Path


def load_data(filepath: str) -> pd.DataFrame:
    """Load and prepare the CSV data."""
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['day_of_week'] = df['datetime'].dt.dayofweek  # 0=Monday, 4=Friday
    df['day_name'] = df['datetime'].dt.day_name()
    df['week'] = df['datetime'].dt.isocalendar().week
    df['year'] = df['datetime'].dt.year
    return df


def find_matching_weeks(df: pd.DataFrame) -> list[dict]:
    """
    Find weeks where Mon, Tue, Wed are all bullish.
    Returns list of week data with Friday outcome.
    """
    results = []

    # Group by year-week
    df['year_week'] = df['year'].astype(str) + '-' + df['week'].astype(str).str.zfill(2)

    for year_week, week_df in df.groupby('year_week'):
        week_df = week_df.sort_values('datetime')

        # Get each day's data
        days = {row['day_of_week']: row for _, row in week_df.iterrows()}

        # Need Mon(0), Tue(1), Wed(2), Thu(3), Fri(4)
        if not all(d in days for d in [0, 1, 2, 3, 4]):
            continue

        mon = days[0]
        tue = days[1]
        wed = days[2]
        thu = days[3]
        fri = days[4]

        # Check hypothesis condition: Mon, Tue, Wed, Thu all red
        mon_red = mon['Close'] < mon['Open']
        tue_red = tue['Close'] < tue['Open']
        wed_red = wed['Close'] < wed['Open']
        thu_red = thu['Close'] < thu['Open']

        if mon_red and tue_red and wed_red and thu_red:
            # Friday outcome
            fri_green = fri['Close'] > fri['Open']

            results.append({
                'year_week': year_week,
                'mon_date': mon['datetime'],
                'mon_close': mon['Close'],
                'tue_close': tue['Close'],
                'wed_close': wed['Close'],
                'thu_close': thu['Close'],
                'fri_open': fri['Open'],
                'fri_close': fri['Close'],
                'fri_change_pct': (fri['Close'] - fri['Open']) / fri['Open'] * 100,
                'fri_is_green': fri_green,
                'hypothesis_correct': fri_green
            })

    return results


def analyze_results(results: list[dict]) -> dict:
    """Analyze the hypothesis results."""
    if not results:
        return {'error': 'No matching weeks found'}

    total = len(results)
    correct = sum(1 for r in results if r['hypothesis_correct'])
    incorrect = total - correct

    fri_changes = [r['fri_change_pct'] for r in results]

    return {
        'total_matching_weeks': total,
        'hypothesis_correct': correct,
        'hypothesis_incorrect': incorrect,
        'accuracy_pct': correct / total * 100,
        'avg_friday_change_pct': sum(fri_changes) / len(fri_changes),
        'min_friday_change_pct': min(fri_changes),
        'max_friday_change_pct': max(fri_changes),
    }


def main():
    data_path = Path(__file__).parent.parent.parent.parent / 'data' / 'time_series' / 'EUR_USD_1day.csv'

    print("=" * 60)
    print("Bullish Week Start Hypothesis Analysis")
    print("=" * 60)
    print("\nHypothesis: If Mon, Tue, Wed, Thu are all red (close < open),")
    print("            then Friday will be green (close > open)")
    print("-" * 60)

    df = load_data(data_path)
    print(f"\nLoaded {len(df)} daily records")
    print(f"Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}")

    results = find_matching_weeks(df)
    print(f"\nFound {len(results)} weeks matching the condition")
    print("(Mon, Tue, Wed, Thu all red)")

    if not results:
        print("No matching weeks found!")
        return

    analysis = analyze_results(results)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total matching weeks:    {analysis['total_matching_weeks']}")
    print(f"Friday was green:        {analysis['hypothesis_correct']} ({analysis['accuracy_pct']:.1f}%)")
    print(f"Friday was NOT green:    {analysis['hypothesis_incorrect']} ({100 - analysis['accuracy_pct']:.1f}%)")
    print(f"\nFriday price change statistics:")
    print(f"  Average: {analysis['avg_friday_change_pct']:+.4f}%")
    print(f"  Min:     {analysis['min_friday_change_pct']:+.4f}%")
    print(f"  Max:     {analysis['max_friday_change_pct']:+.4f}%")

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    if analysis['accuracy_pct'] > 50:
        print(f"Hypothesis SUPPORTED: {analysis['accuracy_pct']:.1f}% of Fridays were green")
    else:
        print(f"Hypothesis NOT SUPPORTED: Only {analysis['accuracy_pct']:.1f}% of Fridays were green")

    # Show some examples
    print("\n" + "=" * 60)
    print("SAMPLE WEEKS (first 10)")
    print("=" * 60)
    for r in results[:10]:
        status = "CORRECT" if r['hypothesis_correct'] else "WRONG"
        print(f"{r['mon_date'].date()} | Fri: {r['fri_change_pct']:+.4f}% | {status}")


if __name__ == '__main__':
    main()
