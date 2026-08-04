"""First-turn user prompt augmentation.

The UI knows which chart the user is looking at (symbol, interval, active
indicators) but not what the market has actually done today. This middleware
joins the two: on the first message of a thread it takes the raw question and
re-renders it through USER_PROMPT_TEMPLATE, adding live session and volatility
context fetched from TwelveData.

Only the first message is augmented — later turns inherit the context from the
conversation history, so re-sending it would just burn tokens.
"""

import asyncio
import logging

from langchain.agents.middleware import before_agent
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from agent.prompts.user_prompt_template import build_user_prompt
from agent.services.technical import MarketStatisticsService, SessionContextService
from agent.states_and_contexts.technical_analysis import OrchestratorContext, OrchestratorState

logger = logging.getLogger(__name__)

RANGE_LOOKBACK = 20
_UNAVAILABLE = "Not available."


def _fetch_market_context(symbol: str, asset_type) -> tuple[str, str]:
    """Fetch session + daily-range summaries. Blocking; call via asyncio.to_thread.

    Each summary is fetched independently so one failing provider call still
    leaves the other in the prompt. A missing summary is never fatal: the agent
    can always fall back to its own tools.
    """
    session_summary = _UNAVAILABLE
    range_summary = _UNAVAILABLE
    is_live = True

    try:
        snapshot = SessionContextService().get_snapshot(symbol, asset_type)
        session_summary = snapshot.summary
        is_live = snapshot.is_live
    except Exception:
        logger.warning("Session context unavailable for %s", symbol, exc_info=True)

    try:
        stats = MarketStatisticsService(
            symbol=symbol, timezone="UTC", asset_type=asset_type
        ).get_daily_range_context(lookback=RANGE_LOOKBACK, is_live=is_live)
        range_summary = stats.summary
    except Exception:
        logger.warning("Range context unavailable for %s", symbol, exc_info=True)

    return session_summary, range_summary


@before_agent
async def augment_first_user_message(
    state: OrchestratorState, runtime: Runtime[OrchestratorContext]
) -> dict | None:
    """Rewrite the opening question into the full user prompt template."""
    messages = state["messages"]

    # A single message means the thread has just started. Any later turn already
    # carries the context in its history.
    if len(messages) != 1:
        return None

    first = messages[0]
    if not isinstance(first, HumanMessage) or first.id is None:
        return None

    context = runtime.context
    symbol = getattr(context, "symbol", None)
    if not symbol:
        # Older clients don't send chart state; leave the question untouched.
        return None

    asset_type = getattr(context, "asset_type", None)
    session_summary, range_summary = await asyncio.to_thread(
        _fetch_market_context, symbol, asset_type
    )

    content = first.content if isinstance(first.content, str) else first.text()
    augmented = build_user_prompt(
        user_question=content,
        asset=symbol,
        chart_interval=getattr(context, "interval", None) or "not specified",
        technical_indicators=getattr(context, "indicators", None) or "none",
        session_context=session_summary,
        range_context=range_summary,
    )

    # Same id => the add_messages reducer replaces the message rather than
    # appending a second copy of the question.
    return {"messages": [HumanMessage(content=augmented, id=first.id)]}
