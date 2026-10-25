from langchain.agents import AgentState
from typing_extensions import Annotated, TypedDict
from typing import Literal, NotRequired
import operator
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema
from typing import Literal, Optional

from agent.utils.llm import DEFAULT_REASONING_EFFORT, ReasoningEffort
from agent.utils.twelve_data import AssetType

def replace_todos(current: list | None, new: list) -> list:
    """Reducer that replaces todos with the latest value (last writer wins)."""
    return new

# ========================================
# Quant Agent
# ========================================
class QuantAgentState(AgentState):
    """State for the quantitative analysis agent."""
    # Use Annotated with operator.add to allow concurrent updates from parallel tool calls
    downloaded_files: Annotated[list[str], operator.add]

@dataclass
class QuantAgentContext:
    """Runtime context for the quant analysis agent."""

    model_name: str = "google/gemini-3.8-flash"
    reasoning_effort: ReasoningEffort = DEFAULT_REASONING_EFFORT
    max_iterations: int = 10
    session_data_dir: str | None = None  # Session-specific temp directory for data files
    asset_type: AssetType | None = None  # Asset type for market hours filtering

# ========================================
# Chart Agent
# ========================================
class ChartAgentContext(BaseModel):
    """What chart the agent should build, and the context to build it in.

    Doubles as the `task` tool's argument and as the agent's runtime context:
    the tool fills it from the orchestrator's argument list, and the agent's
    before_agent middleware turns it into the chart image plus the user message.
    """

    asset: str
    interval: Literal["1min", "5min", "15min", "1h", "4h", "1day", "1week"]
    indicator: Literal["ema", "rsi", "macd", "atr", "bb", "pivot", "none"]
    size: int = 80
    end_date: Optional[str] = None
    # Injected by the tool from OrchestratorContext, never by the model: kept out
    # of the JSON schema the orchestrator sees.
    asset_type: SkipJsonSchema[AssetType | None] = None

# ========================================
# Orchestrator Agent
# ========================================
class Todo(BaseModel):
    content: str
    status: Literal["pending", "in_progress", "completed"]

class OrchestratorState(AgentState):
    todos: Annotated[list[Todo], replace_todos]

@dataclass
class OrchestratorContext:
    model_name: str = "google/gemini-3.8-flash"
    subagent_model_name: str = "google/gemini-3.8-flash"
    reasoning_effort: ReasoningEffort = DEFAULT_REASONING_EFFORT
    # Effort for the chart/quant subagents. Kept separate from the
    # orchestrator's so a run can think hard about planning while the
    # subagents stay cheap, or the other way round.
    subagent_reasoning_effort: ReasoningEffort = DEFAULT_REASONING_EFFORT
    max_research_iterations: int = 5
    max_concurrent_tasks: int = 4
    min_research_iterations: int = 2
    asset_type: AssetType | None = None  # Asset type for market hours filtering
    # Chart the user is looking at in the UI. Used to build the first-turn user
    # prompt (see agents/user_context.py); the UI is the source of truth here.
    symbol: str | None = None
    interval: str | None = None
    indicators: str | None = None  # comma-separated labels, e.g. "EMA 20, RSI"