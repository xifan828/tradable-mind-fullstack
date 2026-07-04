# """LangGraph single-node graph template.

# Returns a predefined response. Replace logic and configuration as needed.
# """

# from __future__ import annotations

# from dataclasses import dataclass
# from typing import Any, Dict

# from langgraph.graph import StateGraph
# from langgraph.runtime import Runtime
# from typing_extensions import TypedDict


# class Context(TypedDict):
#     """Context parameters for the agent.

#     Set these when creating assistants OR when invoking the graph.
#     See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
#     """

#     my_configurable_param: str


# @dataclass
# class State:
#     """Input state for the agent.

#     Defines the initial structure of incoming data.
#     See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
#     """

#     changeme: str = "example"


# async def call_model(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
#     """Process input and returns output.

#     Can use runtime context to alter behavior.
#     """
#     return {
#         "changeme": "output from call_model. "
#         f"Configured with {(runtime.context or {}).get('my_configurable_param')}"
#     }


# # Define the graph
# graph = (
#     StateGraph(State, context_schema=Context)
#     .add_node(call_model)
#     .add_edge("__start__", "call_model")
#     .compile(name="New Graph")
# )

from agent.agents.orchestrator import orchestrator_agent

graph = orchestrator_agent

# model = ChatGoogleGenerativeAI(
#     model="gemini-3.5-flash", google_api_key=os.getenv("GEMINI_API_KEY")
# )

# agent = create_agent(
#     model=model,
#     system_prompt="You are a helpful assistant. Keep your answers concise and to the point.",
#     name="Gemini Agent",
# )

# graph = agent
