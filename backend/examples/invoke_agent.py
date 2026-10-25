"""Invoke the orchestrator agent in-process — no frontend, no `langgraph dev`.

`src/agent/graph.py` just re-exports the compiled LangChain agent, so you can
call it directly from Python like any other LangGraph runnable. The LangGraph
dev server (and all its HTTP/thread/stream plumbing) is only needed by the
browser frontend.

Usage (from backend/, with the project venv):

    uv run python examples/invoke_agent.py "What is the current price of EUR/USD?"
    uv run python examples/invoke_agent.py "How does this chart look?" \
        --symbol EUR/USD --interval 1h --indicators "EMA 20, RSI"
    uv run python examples/invoke_agent.py "Say pong" --stream

Requires TD_API_KEY and OPENROUTER_API_KEY in backend/.env.
"""

import argparse
import asyncio
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from agent.graph import graph
from agent.states_and_contexts.technical_analysis import OrchestratorContext
from agent.utils.llm import DEFAULT_REASONING_EFFORT, REASONING_EFFORTS

load_dotenv()


def message_text(message) -> str:
    """Flatten a message's content, which may be a string or content blocks."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") for block in content if isinstance(block, dict)
    )


def build_context(args: argparse.Namespace) -> OrchestratorContext:
    """Build the runtime context the agent reads via `request.runtime.context`.

    Passing `symbol`/`interval`/`indicators` also switches on the first-turn
    prompt augmentation (see agents/user_context.py): the chart state from the
    UI is what the frontend would have sent.
    """
    return OrchestratorContext(
        model_name=args.model,
        reasoning_effort=args.reasoning_effort,
        subagent_model_name=args.subagent_model,
        subagent_reasoning_effort=args.subagent_reasoning_effort,
        asset_type=args.asset_type,
        symbol=args.symbol,
        interval=args.interval,
        indicators=args.indicators,
    )


async def run(args: argparse.Namespace) -> None:
    context = build_context(args)
    # A message id is required for the first-turn prompt rewrite: the middleware
    # replaces the message by id instead of appending a second copy.
    payload = {"messages": [HumanMessage(content=args.query, id=str(uuid4()))]}
    config = {"configurable": {"thread_id": str(uuid4())}}

    if not args.stream:
        result = await graph.ainvoke(payload, config=config, context=context)
        print(message_text(result["messages"][-1]))
        return

    async for chunk in graph.astream(
        payload, config=config, context=context, stream_mode="messages"
    ):
        token, metadata = chunk
        text = message_text(token)
        if text:
            print(f"[{metadata.get('langgraph_node')}] {text}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="The user question to send to the agent.")
    parser.add_argument("--asset-type", default="forex")
    parser.add_argument("--symbol", default=None, help="Chart symbol, e.g. EUR/USD.")
    parser.add_argument("--interval", default=None, help="Chart interval, e.g. 1h.")
    parser.add_argument(
        "--indicators", default=None, help='Active indicators, e.g. "EMA 20, RSI".'
    )
    parser.add_argument("--model", default="google/gemini-3.8-flash")
    parser.add_argument("--subagent-model", default="google/gemini-3.8-flash")
    parser.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        default=DEFAULT_REASONING_EFFORT,
        help="Orchestrator thinking budget (default: %(default)s).",
    )
    parser.add_argument(
        "--subagent-reasoning-effort",
        choices=REASONING_EFFORTS,
        default=DEFAULT_REASONING_EFFORT,
        help="Chart/quant subagent thinking budget (default: %(default)s).",
    )
    parser.add_argument(
        "--stream", action="store_true", help="Print tokens as they arrive."
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
