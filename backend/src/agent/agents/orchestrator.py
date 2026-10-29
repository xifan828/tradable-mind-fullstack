from pathlib import Path
from typing import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest, ModelResponse, wrap_model_call
from langgraph.checkpoint.memory import InMemorySaver

from agent.states_and_contexts.technical_analysis import OrchestratorState, OrchestratorContext
from agent.tools.todo_tools import write_todos, read_todos
from agent.tools.think_tool import think_tool
from agent.tools.task_tool import task
from agent.tools.post_tool import post_to_x
from agent.agents.user_context import augment_first_user_message
from agent.utils.llm import build_openrouter_model

ORCHESTRATOR_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "orchestrator.md"
ORCHESTRATOR_SYSTEM_PROMPT = ORCHESTRATOR_PROMPT_PATH.read_text(encoding="utf-8")


@wrap_model_call
async def dynamic_model_from_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Use the model the caller picked for this run (OrchestratorContext)."""
    # The OpenRouter key always comes from OPENROUTER_API_KEY (backend/.env);
    # the caller never supplies one.
    model = build_openrouter_model(
        request.runtime.context.model_name,
        reasoning_effort=getattr(request.runtime.context, "reasoning_effort", None),
    )

    return await handler(request.override(model=model))


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
    # tools=[write_todos, read_todos, think_tool, task],
    tools=[write_todos, read_todos, task, post_to_x],
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    state_schema=OrchestratorState,
    context_schema=OrchestratorContext,
    middleware=[
        augment_first_user_message,
        dynamic_model_from_context,
        orchestrator_system_prompt_from_context,
    ],
    #checkpointer=checkpointer
)