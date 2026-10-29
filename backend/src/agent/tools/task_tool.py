from typing import Literal
from uuid import uuid4

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage

from agent.agents.chart_agent import chart_agent
from agent.agents.quant_agent import quant_agent
from agent.prompts.technical_analysis import TASK_DESCRIPTION
from agent.states_and_contexts.technical_analysis import (
    ChartAgentContext,
    QuantAgentContext,
)
from agent.tools.quant_tools import aclose_run
from agent.utils.llm import parse_langchain_ai_message


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
        # One code execution session per run, identified by this id: it holds the
        # agent's variables across its tool calls and is closed in the `finally`
        # below, on the success and the failure path alike.
        run_id = uuid4().hex
        # The quant agent's model comes from backend/.env, not from the
        # orchestrator's context, so only the run wiring is passed here.
        quant_context = QuantAgentContext(
            asset_type=context.asset_type,
            run_id=run_id,
        )

        try:
            result = await quant_agent.ainvoke(
                {"messages": [HumanMessage(content=task_description)]},
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
            # The session is a real process holding the run's DataFrames. Close it
            # here rather than in an after_agent hook: hooks inside the agent do
            # not run when the run raises or is cancelled, which is exactly when a
            # leaked process would sit around holding memory. The async close
            # keeps the reap wait off the event loop.
            await aclose_run(run_id)

    else:
        return f"Error: Unknown task_type '{task_type}'. Must be 'chart' or 'quantitative'."
