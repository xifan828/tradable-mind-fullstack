from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage
from typing import Literal
import asyncio
import random
import shutil
from pathlib import Path

from agent.agents.chart_agent import chart_analysis_agent, chart_description_agent
from agent.agents.quant_agent import quant_agent
from agent.services.technical.technical_indicator import TechnicalIndicatorService
from agent.prompts.technical_analysis import CHART_DESCRIPTION_USER_PROMPT, CHART_ANALYSIS_USER_PROMPT, TASK_DESCRIPTION
from agent.utils.constants import get_decimal_places
from agent.utils.llm import parse_langchain_ai_message
from agent.states_and_contexts.technical_analysis import ChartAnalysisInput, QuantAgentContext, ChartAgentContext
from agent.config.settings import BASE_DIR

# Base directory for session temp directories
QUANT_DATA_BASE_DIR = BASE_DIR / "data" / "time_series"


class ChartAnalysisTask:
    def __init__(
            self,
            task_description: str,
            analysis_input: ChartAnalysisInput,
            # asset: str,
            # interval: str,
            # indicator: Literal["ema", "rsi", "macd", "atr", "bb", "pivot", "none"],
            # size: int,
            # end_date: str,
            context: ChartAgentContext | None = None
    ):  
        
        self.task_description = task_description
        self.asset = analysis_input.asset
        self.interval = analysis_input.interval
        self.indicator = analysis_input.indicator
        self.size = analysis_input.size
        self.end_date = analysis_input.end_date
        self.context = context
    
    def prepare_chart_and_context(self) -> tuple[str, str, float]:  # encoded_chart, extra_context, current_price
        service = TechnicalIndicatorService(
            symbol=self.asset,
            interval=self.interval,
            timezone="UTC",
            asset_type=self.context.asset_type if self.context else None
        )
        df = service.prepare_data(
            data_source="TwelveData",
            outputsize=self.size,
            end_date=self.end_date
        )

        decimal_places = get_decimal_places(self.asset)
        current_price = df["Close"].round(decimal_places).iloc[-1]

        pivot_levels = None

        if self.indicator == "pivot":
            pivot_levels = service.get_pivot_levels()
            encoded_chart = service.prepare_chart(
                df=df,
                size=self.size,
                analysis_type=self.indicator,
                pivot_levels=pivot_levels
            )

        else:
            encoded_chart = service.prepare_chart(
                df=df,
                size=self.size,
                analysis_type=self.indicator,
            )

        extra_context = service.prepare_extra_context(
            df=df,
            analysis_type=self.indicator,
            decimal_places=decimal_places,
            pivot_levels=pivot_levels
        )

        return encoded_chart, extra_context, current_price
    
    async def synthesize_chart_description(self, encoded_chart: str, extra_context: str, current_price: float) -> str:

        text_prompt = CHART_DESCRIPTION_USER_PROMPT.format(
            size=self.size,
            interval=self.interval,
            asset=self.asset,
            analysis_type=self.indicator,
            current_price=current_price,
            extra_context=extra_context
        )
        human_message = HumanMessage(
        content=[
            {"type": "text", "text": text_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_chart}"},
            },
            ]
        )
        result = await chart_description_agent.ainvoke(
            {"messages": [human_message]},
            context=self.context
        )
        chart_description = result["messages"][-1].content[0]["text"]
        return chart_description
    
    async def synthesize_technical_analysis(self, encoded_chart: str, chart_description: str, current_price: float) -> str:

        text_prompt = CHART_ANALYSIS_USER_PROMPT.format(
            task_description=self.task_description,
            chart_description=chart_description,
            size=self.size,
            interval=self.interval,
            asset=self.asset,
            analysis_type=self.indicator,
            current_price=current_price,
    
        )
        human_message = HumanMessage(
        content=[
            {"type": "text", "text": text_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_chart}"},
            },
            ]
        )
        result = await chart_analysis_agent.ainvoke(
            {"messages": [human_message]},
            context=self.context
        )
        technical_analysis = result["messages"][-1].content[0]["text"]
        return technical_analysis
    
    async def execute(self) -> str:
        encoded_chart, extra_context, current_price = await asyncio.to_thread(self.prepare_chart_and_context)
        chart_description = await self.synthesize_chart_description(
            encoded_chart=encoded_chart,
            extra_context=extra_context,
            current_price=current_price
        )
        technical_analysis = await self.synthesize_technical_analysis(
            encoded_chart=encoded_chart,
            chart_description=chart_description,
            current_price=current_price
        )
        return technical_analysis

@tool(description=TASK_DESCRIPTION, parse_docstring=True)
async def task(
    runtime: ToolRuntime,
    task_type: Literal["chart", "quantitative"],
    task_description: str,
    chart_analysis_input: ChartAnalysisInput | None = None
) -> str:
    """Execute a technical analysis task.

    Args:
        task_type: Type of analysis to perform - "chart" for visual chart analysis
            or "quantitative" for data-driven quantitative analysis.
        task_description: Description of the analysis task to perform.
        chart_analysis_input: Required for chart tasks. Contains asset, interval,
            indicator type, size, and optional end_date. 

    Returns:
        The analysis result as a string.
    """
    context = runtime.context
    if task_type == "chart":
        if chart_analysis_input is None:
            return "Error: chart_analysis_input is required for chart analysis tasks."
        chart_context = ChartAgentContext(
            api_key=context.api_key,
            model_name=context.subagent_model_name,
            asset_type=context.asset_type
        )

        chart_task = ChartAnalysisTask(
            task_description=task_description,
            analysis_input=chart_analysis_input,
            context=chart_context
        )

        try:
            return await chart_task.execute()
        except ValueError as e:
            return f"Error: Unable to fetch data for asset '{chart_analysis_input.asset}'. {str(e)}. Verify the asset symbol. Positive: 'AAPL' for stocks, 'EUR/USD' for forex, 'BTC/USD' for crypto, XAU/USD for commodity."
        except Exception as e:
            error_msg = str(e)
            if "symbol" in error_msg.lower() or "invalid" in error_msg.lower():
                return f"Error: The symbol '{chart_analysis_input.asset}' is not recognized or invalid. Please check if the symbol format is correct (e.g., 'EUR/USD' for forex, 'AAPL' for stocks, 'BTC/USD' for crypto)."
            return f"Error: Failed to complete chart analysis for '{chart_analysis_input.asset}'. {error_msg}"

    elif task_type == "quantitative":
        from langchain_core.messages import HumanMessage

        # Create session-specific temp directory with random 6-digit number
        session_id = f"{random.randint(100000, 999999)}"
        session_data_dir = QUANT_DATA_BASE_DIR / session_id
        await asyncio.to_thread(session_data_dir.mkdir, parents=True, exist_ok=True)

        quant_context = QuantAgentContext(
            api_key=context.api_key,
            model_name=context.subagent_model_name,
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
                return last_msg.content[0]["text"]
            return "No response from quantitative agent."
        finally:
            # Clean up session temp directory
            if await asyncio.to_thread(session_data_dir.exists):
                await asyncio.to_thread(shutil.rmtree, session_data_dir, True)

    else:
        return f"Error: Unknown task_type '{task_type}'. Must be 'chart' or 'quantitative'."