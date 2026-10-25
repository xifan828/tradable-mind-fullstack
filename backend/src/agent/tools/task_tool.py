import asyncio
import random
import shutil
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage

from agent.agents.chart_agent import chart_agent
from agent.agents.quant_agent import quant_agent
from agent.config.settings import BASE_DIR
from agent.prompts.technical_analysis import TASK_DESCRIPTION
from agent.states_and_contexts.technical_analysis import (
    ChartAgentContext,
    QuantAgentContext,
)
from agent.utils.llm import parse_langchain_ai_message

# Base directory for session temp directories
QUANT_DATA_BASE_DIR = BASE_DIR / "data" / "time_series"


@tool(description=TASK_DESCRIPTION, parse_docstring=True)
async def task(
    runtime: ToolRuntime,
    task_type: Literal["chart", "quantitative"],
    task_description: str,
    chart_context: ChartAgentContext | None = None
) -> str:
    """Execute a technical analysis task.

    Args:
        task_type: Type of analysis to perform - "chart" for visual chart analysis
            or "quantitative" for data-driven quantitative analysis.
        task_description: Description of the analysis task to perform.
        chart_context: Required for chart tasks. The chart to analyse: asset,
            interval, indicator, size and optional end_date. Leave empty for
            quantitative tasks.

    Returns:
        The analysis result as a string.
    """
    context = runtime.context
    if task_type == "chart":
        if chart_context is None:
            return "Error: chart_context is required for chart analysis tasks."

        # The chart agent draws the chart itself: its before_agent middleware
        # turns this context plus the task description into the multimodal user
        # message. Only the asset type comes from the orchestrator's context.
        chart_context = chart_context.model_copy(
            update={"asset_type": context.asset_type}
        )

        try:
            result = await chart_agent.ainvoke(
                {"messages": [HumanMessage(content=task_description)]},
                context=chart_context,
            )
            return parse_langchain_ai_message(result["messages"][-1])
        except ValueError as e:
            return f"Error: Unable to fetch data for asset '{chart_context.asset}'. {str(e)}. Verify the asset symbol. Positive: 'AAPL' for stocks, 'EUR/USD' for forex, 'BTC/USD' for crypto, XAU/USD for commodity."
        except Exception as e:
            error_msg = str(e)
            if "symbol" in error_msg.lower() or "invalid" in error_msg.lower():
                return f"Error: The symbol '{chart_context.asset}' is not recognized or invalid. Please check if the symbol format is correct (e.g., 'EUR/USD' for forex, 'AAPL' for stocks, 'BTC/USD' for crypto)."
            return f"Error: Failed to complete chart analysis for '{chart_context.asset}'. {error_msg}"

    elif task_type == "quantitative":
        # Create session-specific temp directory with random 6-digit number
        session_id = f"{random.randint(100000, 999999)}"
        session_data_dir = QUANT_DATA_BASE_DIR / session_id
        await asyncio.to_thread(session_data_dir.mkdir, parents=True, exist_ok=True)

        quant_context = QuantAgentContext(
            model_name=context.subagent_model_name,
            reasoning_effort=context.subagent_reasoning_effort,
            session_data_dir=str(session_data_dir),
            asset_type=context.asset_type,
        )

        try:
            result = await quant_agent.ainvoke(
                {"messages": [HumanMessage(content=task_description)], "downloaded_files": []},
                context=quant_context
            )

            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                return parse_langchain_ai_message(last_msg)
            return "No response from quantitative agent."
        except Exception as e:
            # Same guard as the chart branch: ToolNode re-raises anything that
            # escapes a tool, which aborts the whole run (the orchestrator never
            # gets a result to react to). A subagent failure — a network error on
            # one of its model calls, say — has to come back as a tool result it
            # can retry or work around.
            return (
                f"Error: Failed to complete the quantitative analysis "
                f"({type(e).__name__}). {str(e)} "
                "The task did not finish; you can retry it or continue without its result."
            )
        finally:
            # Clean up session temp directory
            if await asyncio.to_thread(session_data_dir.exists):
                await asyncio.to_thread(shutil.rmtree, session_data_dir, True)

    else:
        return f"Error: Unknown task_type '{task_type}'. Must be 'chart' or 'quantitative'."
