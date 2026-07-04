from langchain.tools import ToolRuntime, tool
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from agent.states_and_contexts.technical_analysis import Todo, OrchestratorState
from agent.prompts.technical_analysis import WRITE_TODOS_DESCRIPTION, READ_TODOS_DESCRIPTION

@tool(description=WRITE_TODOS_DESCRIPTION, parse_docstring=True)
def write_todos(todos: list[Todo], runtime: ToolRuntime) -> str:
    """Writes down a list of analysis tasks to be completed.
    
    Args:
        todos: List of Todo items with content and status
    """

    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(
                    content=f"Updated todos list with {todos}.",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        }
    )

@tool(description=READ_TODOS_DESCRIPTION)
def read_todos(runtime: ToolRuntime) -> str:
    
    todos = runtime.state.get("todos", [])
    if not todos:
        return "No todos found."
    result = ""
    for idx, todo in enumerate(todos):
        result += f"{idx+1}. {todo.content} - Status: {todo.status}\n"
    return result.strip()


