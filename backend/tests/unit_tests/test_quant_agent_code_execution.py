"""The quant agent end to end: one session across tool calls, closed afterwards.

The model and the data provider are stubbed, so this runs offline; everything
else is the real wiring — the quant agent, its middleware, the `code_execution`
tool, the session registry and the `task` tool's teardown.
"""

import asyncio
import os
from types import SimpleNamespace

import pandas as pd
import pytest
from blockbuster import blockbuster_ctx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent.agents.quant_agent import build_quant_agent
from agent.states_and_contexts.technical_analysis import OrchestratorContext
from agent.tools import quant_tools, task_tool
from agent.tools.quant_tools import _SESSIONS, ReplSession, code_execution
from agent.tools.task_tool import task


class ScriptedModel(BaseChatModel):
    """A model that replays a fixed script of messages."""

    script: list = []
    index: int = 0
    seen_system_prompt: str = ""
    seen: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools=None, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if not self.index:
            first = messages[0]
            self.seen_system_prompt = getattr(first, "content", "")
        self.seen.append([str(getattr(m, "content", "")) for m in messages])
        message = self.script[self.index]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def _call(code: str, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "code_execution", "args": {"code": code}, "id": call_id, "type": "tool_call"}
        ],
    )


@pytest.fixture
def stub_data(monkeypatch):
    """Serve download_market_data from an in-process frame instead of the API."""

    def fake_fetch(self, ticker, interval, **kwargs):
        return pd.DataFrame(
            {
                "Date": pd.date_range("2026-01-01", periods=60, freq="4h"),
                "Open": range(60),
                "High": range(1, 61),
                "Low": range(60),
                "Close": [100.0 + i for i in range(60)],
                "EMA20": [100.0] * 60,
                "EMA50": [95.0] * 60,
            }
        )

    monkeypatch.setattr(ReplSession, "fetch_market_data", fake_fetch)
    return fake_fetch


def test_quant_run_keeps_variables_and_closes_its_session(stub_data, monkeypatch):
    model = ScriptedModel(
        script=[
            _call('df = download_market_data("EUR/USD", "4h")\nlen(df)', "c1"),
            _call('df["gap"] = df["EMA20"] - df["EMA50"]\ndf["gap"].mean()', "c2"),
            AIMessage(content="Trend is flat: EMA20 sits above EMA50 on all 60 bars."),
        ]
    )
    # The quant agent's model comes from backend/.env and is bound when its graph
    # is built, so the stub is injected by rebuilding the graph with it.
    monkeypatch.setattr(task_tool, "quant_agent", build_quant_agent(model))

    runtime = SimpleNamespace(
        context=OrchestratorContext(asset_type="forex"),
        tool_call_id="task-1",
    )
    answer = asyncio.run(
        task.coroutine(
            runtime=runtime,
            task_type="quantitative",
            task_description="Quantify the EMA20/EMA50 gap on EUR/USD 4h.",
        )
    )

    assert "flat" in answer
    # The system prompt is the quant_agent.md the agent reads, and it tells the
    # model the session persists between calls.
    assert "persistent Python REPL" in model.seen_system_prompt
    # The data helper is described by the tool the model is given.
    assert "download_market_data" in code_execution.description
    # Two calls, one namespace: the second call saw the frame the first downloaded
    # (60x7), added a column to it, and the result the model then read shows the
    # same object with 8 columns — without a re-download.
    assert any("df (DataFrame(60, 7))" in text for text in model.seen[1])
    assert any("df (DataFrame(60, 8))" in text for text in model.seen[2])
    # And the run left nothing behind.
    assert _SESSIONS == {}


def test_task_tool_reaches_the_end_of_a_run_without_ever_blocking(stub_data, monkeypatch):
    """Same contract as the langgraph dev server: no blocking call in the loop.

    The run is executed under BlockBuster, which raises on any call that would
    hold up the event loop — the session teardown above all, since it waits for a
    SIGKILLed process to be reaped.
    """
    model = ScriptedModel(
        script=[
            _call('df = download_market_data("EUR/USD", "4h")\nlen(df)', "c1"),
            AIMessage(content="60 bars, no gap."),
        ]
    )
    monkeypatch.setattr(task_tool, "quant_agent", build_quant_agent(model))

    runtime = SimpleNamespace(
        context=OrchestratorContext(asset_type="forex"),
        tool_call_id="task-blocking",
    )

    async def run() -> str:
        # Active only around the run itself: asyncio's own shutdown must not be
        # part of what is being measured.
        with blockbuster_ctx():
            return await task.coroutine(
                runtime=runtime,
                task_type="quantitative",
                task_description="Check EUR/USD 4h for a gap.",
            )

    answer = asyncio.run(run())

    assert "no gap" in answer
    assert _SESSIONS == {}


def test_session_is_closed_even_when_the_agent_raises(monkeypatch):
    """A failed run must not leave a process holding the run's DataFrames."""

    class Boom(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "boom"

        def bind_tools(self, tools=None, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("provider exploded")

    monkeypatch.setattr(task_tool, "quant_agent", build_quant_agent(Boom()))

    runtime = SimpleNamespace(context=OrchestratorContext(asset_type="forex"), tool_call_id="task-2")
    answer = asyncio.run(
        task.coroutine(
            runtime=runtime,
            task_type="quantitative",
            task_description="Anything.",
        )
    )

    assert "Error: Failed to complete the quantitative analysis" in answer
    assert _SESSIONS == {}


def test_active_session_is_an_isolated_process():
    """While the run is alive, its session is a real process of its own."""
    context = SimpleNamespace(run_id="inspect-run", asset_type="forex")
    tool_output = quant_tools.code_execution.func(
        code="x = 41\nx + 1", runtime=SimpleNamespace(context=context)
    )
    session = _SESSIONS["inspect-run"]
    try:
        assert "42" in tool_output
        assert session._process is not None
        assert session._process.poll() is None
        assert session._process.pid != os.getpid()
        assert session.privileged_calls == 0
    finally:
        quant_tools.close_run("inspect-run")

    assert "inspect-run" not in _SESSIONS


def test_session_environment_carries_no_credentials(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-secret")
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "td-secret")

    environment = quant_tools._session_environment("/tmp/workspace")

    assert "OPENROUTER_API_KEY" not in environment
    assert "TWELVE_DATA_API_KEY" not in environment
    assert environment["HOME"] == "/tmp/workspace"
    assert "secret" not in " ".join(environment.values())
