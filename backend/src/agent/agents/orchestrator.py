from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langgraph.checkpoint.memory import InMemorySaver

from agent.states_and_contexts.technical_analysis import OrchestratorState, OrchestratorContext
from agent.tools.todo_tools import write_todos, read_todos
from agent.tools.think_tool import think_tool
from agent.tools.task_tool import task
from agent.agents.quant_agent import dynamic_model_from_context

ORCHESTRATOR_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "orchestrator.md"
ORCHESTRATOR_SYSTEM_PROMPT = ORCHESTRATOR_PROMPT_PATH.read_text(encoding="utf-8")

@dynamic_prompt
def orchestrator_system_prompt_from_context(request: ModelRequest) -> str:
    return ORCHESTRATOR_SYSTEM_PROMPT.format(
        max_concurrent_tasks=request.runtime.context.max_concurrent_tasks,
        max_research_iterations=request.runtime.context.max_research_iterations,
        min_research_iterations=request.runtime.context.min_research_iterations
    )

#checkpointer = InMemorySaver()

orchestrator_agent = create_agent(
    model=None,
    tools=[write_todos, read_todos, think_tool, task],
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    state_schema=OrchestratorState,
    context_schema=OrchestratorContext,
    middleware=[dynamic_model_from_context, orchestrator_system_prompt_from_context],
    #checkpointer=checkpointer
)