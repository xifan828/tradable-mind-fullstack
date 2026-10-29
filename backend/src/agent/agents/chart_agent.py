"""Chart analysis agent: one Gemini call with native code execution.

The agent gets the chart PNG, the task and Gemini's `code_execution` tool, so the
model measures the chart inside Google's sandbox instead of describing it first
and interpreting the description afterwards. The image travels in the human
message as base64 — nothing is written to disk.

Drawing the chart is the agent's own job: a `before_agent` middleware reads the
runtime context (which chart to build), fetches the data, renders the PNG and
rewrites the incoming task description into the multimodal user message. Callers
pass a task description and a context — nothing else.

The model is deliberately not the UI-selected one: it is a Gemini model name
(CHART_AGENT_MODEL) with Google's native code execution, which OpenRouter cannot
proxy.
"""

import asyncio
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState, Runtime, before_agent
from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.config.settings import (
    get_chart_agent_model,
    get_chart_agent_thinking_level,
    get_gemini_api_key,
)
from agent.services.technical.technical_indicator import TechnicalIndicatorService
from agent.states_and_contexts.technical_analysis import ChartAgentContext
from agent.utils.constants import get_decimal_places

# langchain-google-genai turns this into Gemini's server-side code interpreter.
CODE_EXECUTION_TOOL = {"code_execution": {}}
REQUEST_TIMEOUT_SECONDS = 600
MAX_RETRIES = 2

CHART_AGENT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "chart_agent.md"
CHART_AGENT_SYSTEM_PROMPT = CHART_AGENT_PROMPT_PATH.read_text(encoding="utf-8")

# The task description reaches the agent as the plain user message; it is
# rewritten by chart_message_middleware into this template plus the chart image.
CHART_AGENT_USER_PROMPT = """{asset} {interval}, {size} bars, {analysis_type} chart. Current close {current_price}.
Latest values: {extra_context}

Task: {task_description}"""


def build_chart_model(
    model: str | None = None,
    thinking_level: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Build the Gemini chat model used for chart analysis.

    Args:
        model: Gemini model name; defaults to CHART_AGENT_MODEL.
        thinking_level: Gemini 3 thinking level; defaults to
            CHART_AGENT_THINKING_LEVEL and is omitted from the request when unset.

    Returns:
        The chat model, with no tools bound yet.
    """
    params: dict[str, Any] = {
        "model": model or get_chart_agent_model(),
        "api_key": get_gemini_api_key(),
        "timeout": REQUEST_TIMEOUT_SECONDS,
        "max_retries": MAX_RETRIES,
    }
    level = thinking_level or get_chart_agent_thinking_level()
    if level:
        params["thinking_level"] = level

    return ChatGoogleGenerativeAI(**params)


def prepare_chart_payload(context: ChartAgentContext) -> tuple[str, str, float]:
    """Fetch the data for the requested chart and render it.

    Blocking (network + matplotlib); the middleware runs it in a worker thread.

    Args:
        context: Asset, interval, indicator, bar count and optional end date.

    Returns:
        The chart as a base64 PNG, the latest indicator values as text, and the
        latest close rounded to the asset's precision.
    """
    service = TechnicalIndicatorService(
        symbol=context.asset,
        interval=context.interval,
        timezone="UTC",
        asset_type=context.asset_type,
    )
    df = service.prepare_data(
        data_source="TwelveData",
        outputsize=context.size,
        end_date=context.end_date,
    )

    decimal_places = get_decimal_places(context.asset)
    current_price = df["Close"].round(decimal_places).iloc[-1]

    pivot_levels = None
    if context.indicator == "pivot":
        pivot_levels = service.get_pivot_levels()
        encoded_chart = service.prepare_chart(
            df=df,
            size=context.size,
            analysis_type=context.indicator,
            pivot_levels=pivot_levels,
        )
    else:
        encoded_chart = service.prepare_chart(
            df=df,
            size=context.size,
            analysis_type=context.indicator,
        )

    extra_context = service.prepare_extra_context(
        df=df,
        analysis_type=context.indicator,
        decimal_places=decimal_places,
        pivot_levels=pivot_levels,
    )

    return encoded_chart, extra_context, current_price


def build_chart_user_message(
    context: ChartAgentContext,
    task_description: str,
) -> HumanMessage:
    """Build the multimodal user message: the formatted prompt plus the chart.

    Blocking; see `prepare_chart_payload`.
    """
    encoded_chart, extra_context, current_price = prepare_chart_payload(context)

    text_prompt = CHART_AGENT_USER_PROMPT.format(
        asset=context.asset,
        interval=context.interval,
        size=context.size,
        analysis_type=context.indicator,
        current_price=current_price,
        extra_context=extra_context,
        task_description=task_description,
    )

    return HumanMessage(
        content=[
            {"type": "text", "text": text_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded_chart}"},
            },
        ]
    )


def _last_human_message(state: AgentState) -> HumanMessage | None:
    """The most recent human message in the state."""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message
    return None


def _message_text(message: HumanMessage) -> str:
    """The text part of a human message, plain or multimodal."""
    content = message.content
    if isinstance(content, str):
        return content
    return " ".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def _carries_chart(message: Any) -> bool:
    """Whether this message already holds a chart image."""
    content = getattr(message, "content", None)
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "image_url"
        for block in content
    )


@before_agent
async def chart_message_middleware(
    state: AgentState,
    runtime: Runtime[ChartAgentContext],
) -> dict[str, Any] | None:
    """Turn the caller's task description into the chart prompt + image.

    The chart build blocks (TwelveData fetch, matplotlib), so it runs in a worker
    thread instead of stalling the event loop other subagents run on.

    The raw user message is removed rather than left in place: `messages` uses
    the `add_messages` reducer, so returning a message alone would keep the bare
    task text in front of the chart prompt and send both to the model.

    Errors from fetching or rendering propagate out of the agent; the task tool
    turns them into a tool result the orchestrator can react to.
    """
    human = _last_human_message(state)

    # A retry or a resumed run must not draw (and pay for) the chart twice.
    if human is not None and _carries_chart(human):
        return None

    chart_message = await asyncio.to_thread(
        build_chart_user_message,
        runtime.context,
        _message_text(human) if human is not None else "",
    )

    updates: list[Any] = []
    if human is not None and human.id:
        updates.append(RemoveMessage(id=human.id))
    updates.append(chart_message)
    return {"messages": updates}


# ============================================================
# Chart Analysis Agent
# ============================================================
chart_agent = create_agent(
    model=build_chart_model(),
    tools=[CODE_EXECUTION_TOOL],
    system_prompt=CHART_AGENT_SYSTEM_PROMPT,
    context_schema=ChartAgentContext,
    middleware=[chart_message_middleware],
)
