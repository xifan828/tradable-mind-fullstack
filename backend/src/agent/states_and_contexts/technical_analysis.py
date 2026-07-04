from langchain.agents import AgentState
from typing_extensions import Annotated, TypedDict
from typing import Literal, NotRequired
import operator
from dataclasses import dataclass
from pydantic import BaseModel
from typing import Literal, Optional

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
    api_key: str
    model_name: str = "models/gemini-3-flash-preview"
    max_iterations: int = 10
    session_data_dir: str | None = None  # Session-specific temp directory for data files
    asset_type: AssetType | None = None  # Asset type for market hours filtering

# ========================================
# Chart Agent
# ========================================
class ChartAnalysisInput(BaseModel):
    asset: str
    interval: Literal["1min", "5min", "15min", "1h", "4h", "1day", "1week"]
    indicator: Literal["ema", "rsi", "macd", "atr", "bb", "pivot", "none"]
    size: int = 80
    end_date: Optional[str] = None

@dataclass
class ChartAgentContext:
    """Runtime context for the chart analysis agent."""
    api_key: str
    model_name: str = "models/gemini-3-flash-preview"
    asset_type: AssetType | None = None  # Asset type for market hours filtering

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
    api_key: str
    model_name: str = "models/gemini-3-flash-preview"
    subagent_model_name: str = "models/gemini-3-flash-preview"
    max_research_iterations: int = 5
    max_concurrent_tasks: int = 4
    min_research_iterations: int = 2
    asset_type: AssetType | None = None  # Asset type for market hours filtering