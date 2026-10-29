from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain_core.language_models.chat_models import BaseChatModel
from agent.config.settings import (
    get_quant_agent_model,
    get_quant_agent_thinking_level,
)
from agent.utils.llm import build_openrouter_model

from agent.states_and_contexts.technical_analysis import QuantAgentState, QuantAgentContext
from agent.tools.quant_tools import aclose_run, code_execution

QUANT_AGENT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "quant_agent.md"
QUANT_AGENT_SYSTEM_PROMPT = QUANT_AGENT_PROMPT_PATH.read_text(encoding="utf-8")

# ============================================================
# Quantitative Analysis Agent
# ============================================================
# The model is fixed by backend/.env (QUANT_AGENT_MODEL /
# QUANT_AGENT_THINKING_LEVEL), not chosen per run: the quant agent is tuned
# together with the prompt and the REPL tool it drives, so the caller's context
# does not get to swap it out.
quant_agent_model = build_openrouter_model(
    get_quant_agent_model(),
    reasoning_effort=get_quant_agent_thinking_level(),
)

@dynamic_prompt
def quant_agent_system_prompt_from_context(request: ModelRequest) -> str:
    max_iterations = getattr(request.runtime.context, "max_iterations", 10)
    # Plain substitution, not str.format: the markdown prompt is free to contain
    # braces (Python dicts, f-strings in examples) without raising KeyError.
    return QUANT_AGENT_SYSTEM_PROMPT.replace("{max_iterations}", str(max_iterations))

def build_quant_agent(model: BaseChatModel | None = None):
    """Assemble the quant agent graph.

    Args:
        model: Chat model to run the agent on; defaults to `quant_agent_model`,
            which is built from backend/.env. Callers only pass one to swap in a
            stub, as the tests do.
    """
    return create_agent(
        model=model or quant_agent_model,
        tools=[code_execution],
        middleware=[quant_agent_system_prompt_from_context],
        state_schema=QuantAgentState,
        context_schema=QuantAgentContext,
    )


quant_agent = build_quant_agent()

if __name__ == "__main__":
    import asyncio
    import sys
    import textwrap
    import time
    from uuid import uuid4

    from dotenv import load_dotenv
    from langchain_core.messages import BaseMessage, HumanMessage

    from agent.utils.twelve_data import AssetType

    load_dotenv()

    # 10 example prompts to test the agent's capabilities
    EXAMPLE_PROMPTS = [
        # 1. Basic data exploration using pre-calculated indicators
        "Download EUR/USD 4h data and analyze the current trend using the EMA crossovers (EMA10, EMA20, EMA50). Is price above or below the EMAs?",

        # 2. RSI analysis (using pre-calculated RSI14)
        "Download GBP/USD 1h data and find all instances where RSI14 was oversold (<30) or overbought (>70) in the last 200 candles. What happened to price after?",

        # 3. Bollinger Band squeeze detection (using pre-calculated BB)
        "Download XAU/USD 4h data and detect Bollinger Band squeezes where BB_Upper - BB_Lower is at its tightest. These often precede big moves.",

        # 4. MACD divergence analysis (using pre-calculated MACD)
        "Download BTC/USD 1day data and look for potential MACD divergences - where price makes new highs but MACD doesn't, or vice versa.",

        # 5. Candlestick pattern recognition (talib use case)
        "Download EUR/USD 1day data and use talib to scan for candlestick patterns (doji, hammer, engulfing, morning star) in the last 50 candles.",

        # 6. Additional indicator with talib (ADX for trend strength)
        "Download USD/JPY 4h data and calculate ADX using talib to measure trend strength. Is the market trending (ADX>25) or ranging?",

        # 7. Stochastic oscillator (talib - not in pre-calculated data)
        "Download AUD/USD 1h data and calculate Stochastic oscillator using talib. Find recent crossovers between %K and %D lines.",

        # 8. Volatility regime analysis
        "Download EUR/USD 4h data and analyze ATR to identify high and low volatility regimes. Compare current ATR to its 20-period average.",

        # 9. Multi-indicator confluence
        "Download GBP/USD 4h data and find candles where multiple signals align: RSI14 < 40, price below EMA50, and MACD_Diff negative. These are bearish confluences.",

        # 10. Statistical analysis with support/resistance
        "Download XAU/USD 1day data and calculate the mean, std, and percentiles of closing prices. Identify potential support (25th percentile) and resistance (75th percentile) levels.",
    ]

    def print_message(message: BaseMessage, elapsed: float) -> None:
        """Print one tool call or tool result, stamped with the time it arrived."""
        if getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                print(f"\n[{elapsed:5.1f}s] >>> {call['name']}()")
                print(textwrap.indent(call["args"].get("code", ""), "    "))
            return
        if type(message).__name__ != "ToolMessage":
            # The prompt and the model's own prose are printed by the run itself.
            return
        content = str(message.content)
        shown = content if len(content) <= 2500 else content[:2500] + "\n... (truncated for display)"
        print(f"\n[{elapsed:5.1f}s] <<< {getattr(message, 'name', None) or 'tool'} result ({len(content)} chars)")
        print(textwrap.indent(shown, "    "))

    async def run(
        prompt: str,
        asset_type: AssetType = "forex",
    ) -> float:
        """Run one quant agent, printing every tool call and result as it happens.

        Args:
            prompt: The analysis to ask for.
            asset_type: Asset class of the symbol in the prompt ("forex",
                "commodity", "crypto", "stock").

        Returns:
            Wall-clock seconds the run took.
        """
        context = QuantAgentContext(
            asset_type=asset_type,
            run_id=f"manual-{uuid4().hex[:8]}",
        )

        print("=" * 80)
        print(f"MODEL   {get_quant_agent_model()}    run_id {context.run_id}")
        print(f"PROMPT  {prompt}")
        print("=" * 80)

        started = time.perf_counter()
        printed = 0
        messages: list[BaseMessage] = []
        try:
            # stream_mode="values" hands over the whole state after every node, so
            # each tool call and each tool result is printed the moment it exists
            # rather than at the end of the run.
            async for state in quant_agent.astream(
                {"messages": [HumanMessage(content=prompt)]},
                context=context,
                stream_mode="values",
            ):
                messages = state["messages"]
                for message in messages[printed:]:
                    print_message(message, time.perf_counter() - started)
                printed = len(messages)
        finally:
            # Free the run's code execution process as soon as it is finished.
            await aclose_run(context.run_id)

        elapsed = time.perf_counter() - started
        calls = sum(len(m.tool_calls) for m in messages if getattr(m, "tool_calls", None))

        print("\n" + "=" * 80)
        print(f"FINAL ANSWER    {calls} tool call(s)    {elapsed:.2f}s")
        print("=" * 80)
        answer = messages[-1].text.strip() if messages else ""
        if not answer:
            answer = f"(the run ended on a tool call: {messages[-1] if messages else 'no messages'})"
        print(answer[:4000])
        print("=" * 80)
        print(f"[one agent run took {elapsed:.2f}s]")
        return elapsed

    async def main() -> None:
        """Run one agent; use argv to try another prompt or asset type.

        Usage::

            python -m agent.agents.quant_agent
            python -m agent.agents.quant_agent "Download XAU/USD 1day data and summarise it." commodity
        """
        # prompt = sys.argv[1] if len(sys.argv) > 1 else EXAMPLE_PROMPTS[0]
        # prompt = "Perform quantitative statistical analysis on EUR/USD on the 4h and daily timeframes. Calculate current ATR(14) values on 4h and 1d, assess historical distribution of daily ranges, evaluate kinematic exhaustion given today's range of 0.00428 (63% ADR), and identify high liquidity density price nodes / price distribution over the last 80 4h candles. Note: Do not use volume as EUR/USD is forex."
        prompt = "Perform a quantitative analysis of EUR/USD on the 4h and daily timeframes. Calculate 14-period ATR on 4h and daily charts, assess daily range utilization (current range vs 20-day ADR), statistical probability of expansion vs mean reversion from current levels around 1.1151, and key volatility bands. Note: Forex has no volume, rely on OHLC price-derived metrics."
        asset_type: AssetType = sys.argv[2] if len(sys.argv) > 2 else "forex"  # type: ignore[assignment]
        await run(prompt, asset_type)

        # Two runs at once get two independent code execution processes:
        # await asyncio.gather(
        #     run("Download EUR/USD 4h data and check the EMA stack.", "forex"),
        #     run("Download XAU/USD 4h data and check the EMA stack.", "commodity"),
        # )

    asyncio.run(main())
