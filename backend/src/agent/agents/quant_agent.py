from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest, ModelResponse, wrap_model_call
from typing import Callable
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.states_and_contexts.technical_analysis import QuantAgentState, QuantAgentContext
from agent.prompts.technical_analysis import QUANT_AGENT_SYSTEM_PROMPT
from agent.tools.quant_tools import download_market_data, write_code

# ============================================================
# Quantitative Analysis Agent
# ============================================================
@wrap_model_call
async def dynamic_model_from_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    model_name = request.runtime.context.model_name
    api_key = request.runtime.context.api_key

    model = ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key,
        max_retries=0
    )

    return await handler(request.override(model=model))

@dynamic_prompt
def quant_agent_system_prompt_from_context(request: ModelRequest) -> str:
    max_iterations = getattr(request.runtime.context, "max_iterations", 10)
    return QUANT_AGENT_SYSTEM_PROMPT.format(
        max_iterations=max_iterations
    )

quant_agent = create_agent(
    model=None,
    tools=[download_market_data, write_code],
    middleware=[dynamic_model_from_context, quant_agent_system_prompt_from_context],
    state_schema=QuantAgentState,
    context_schema=QuantAgentContext,
)

if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage
    import os
    from dotenv import load_dotenv
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

    async def run_single_agent(agent_id: int, prompt: str, context: QuantAgentContext) -> dict:
        """Run a single agent and return results with timing."""
        import time
        start = time.perf_counter()
        print(f"[Agent {agent_id}] Starting: {prompt[:60]}...")

        result = await quant_agent.ainvoke(
            {"messages": [HumanMessage(content=prompt)], "downloaded_files": []},
            context=context
        )

        elapsed = time.perf_counter() - start
        print(f"[Agent {agent_id}] Completed in {elapsed:.2f}s")
        return {"agent_id": agent_id, "result": result, "elapsed": elapsed}


    # async def main():
    #     import time
    #     import random
    #     import shutil
    #     from agent.config.settings import BASE_DIR

    #     # Create a test session directory
    #     session_id = f"{random.randint(100000, 999999)}"
    #     session_data_dir = BASE_DIR / "data" / "time_series" / session_id
    #     session_data_dir.mkdir(parents=True, exist_ok=True)

    #     context = QuantAgentContext(
    #         api_key=os.getenv("GEMINI_API_KEY"),
    #         model_name="models/gemini-3-flash-preview",
    #         session_data_dir=str(session_data_dir),
    #     )

    #     # Run two agents in parallel to test ProcessPoolExecutor
    #     print("=" * 80)
    #     print("Running TWO agents in PARALLEL to test non-blocking execution")
    #     print("=" * 80)

    #     total_start = time.perf_counter()

    #     # Launch both agents concurrently
    #     results = await asyncio.gather(
    #         # run_single_agent(0, EXAMPLE_PROMPTS[0], context),
    #         # run_single_agent(1, EXAMPLE_PROMPTS[1], context),
    #         # run_single_agent(2, EXAMPLE_PROMPTS[2], context),
    #         # run_single_agent(3, EXAMPLE_PROMPTS[3], context),
    #         # run_single_agent(4, EXAMPLE_PROMPTS[4], context),
    #         run_single_agent(5, "What is the most successfull trading strategy in the last 30 days for USD/JPY.", context),
            
    #         run_single_agent(5, "What is the most successfull trading strategy in the last 30 days for XAU/USD.", context),

            
    #      #   run_single_agent(5, "What is the most successfull trading strategy in the last 30 days for BTC/USD.", context),

    #     )

    #     total_elapsed = time.perf_counter() - total_start

    #     print("\n" + "=" * 80)
    #     print("RESULTS")
    #     print("=" * 80)

    #     for r in results:
    #         print(f"\n[Agent {r['agent_id']}] (completed in {r['elapsed']:.2f}s)")
    #         print("-" * 40)
    #         # Print last message from the agent
    #         messages = r["result"].get("messages", [])
    #         if messages:
    #             last_msg = messages[-1]
    #             content = getattr(last_msg, "content", str(last_msg))
    #             # Truncate long output
    #             if len(content) > 1000:
    #                 content = content[:1000] + "\n... (truncated)"
    #             print(content)

    #     print("\n" + "=" * 80)
    #     print(f"Total wall-clock time: {total_elapsed:.2f}s")
    #     print(f"Sum of individual times: {sum(r['elapsed'] for r in results):.2f}s")
    #     print(f"Parallelism benefit: {sum(r['elapsed'] for r in results) - total_elapsed:.2f}s saved")
    #     print("=" * 80)

    #     # Clean up test session directory
    #     if session_data_dir.exists():
    #         shutil.rmtree(session_data_dir, ignore_errors=True)
    #         print(f"Cleaned up session directory: {session_data_dir}")

    # asyncio.run(main())