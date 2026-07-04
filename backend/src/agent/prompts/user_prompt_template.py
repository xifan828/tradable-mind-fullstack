USER_PROMPT_TEMPLATE = """\
<user_question>
{user_question}
</user_question>

<user_preference>
Asset being analyzed: {asset}. **IMPORTANT, strickly use this asset symbol when delegating tasks to subagents.**
Chart interval: {chart_interval}. This is the main timeframe.
Technical indicators: {technical_indicators}. MUSR use these indicators in the analysis.
</user_preference>

<session-context>
{session_context}
</session-context>

<range-context>
{range_context}
</range-context>
"""


def build_user_prompt(
    user_question: str,
    asset: str,
    chart_interval: str,
    technical_indicators: str,
    session_context: str,
    range_context: str,
) -> str:
    """Render the user prompt template with all required fields.

    Args:
        user_question:        The raw question from the user.
        asset:                Symbol being analyzed, e.g. "EUR/USD".
        chart_interval:       Main timeframe selected in the UI, e.g. "1h".
        technical_indicators: Comma-separated active indicators, e.g. "EMA (10, 20), RSI".
        session_context:      Output of SessionContextService.get_snapshot().summary
        range_context:        Output of MarketStatisticsService.get_daily_range_context().summary
    """
    return USER_PROMPT_TEMPLATE.format(
        user_question=user_question,
        asset=asset,
        chart_interval=chart_interval,
        technical_indicators=technical_indicators,
        session_context=session_context,
        range_context=range_context,
    )
