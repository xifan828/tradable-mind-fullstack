from langchain.agents import create_agent

from agent.agents.quant_agent import dynamic_model_from_context
from agent.states_and_contexts.technical_analysis import ChartAgentContext
from agent.prompts.technical_analysis import CHART_DESCRIPTION_AGENT_SYSTEM_PROMPT, CHART_ANALYSIS_AGENT_SYSTEM_PROMPT

chart_description_agent = create_agent(
    model=None,
    system_prompt=CHART_DESCRIPTION_AGENT_SYSTEM_PROMPT,
    middleware=[dynamic_model_from_context],
    context_schema=ChartAgentContext
)

chart_analysis_agent = create_agent(
    model=None,
    system_prompt=CHART_ANALYSIS_AGENT_SYSTEM_PROMPT,
    middleware=[dynamic_model_from_context],
    context_schema=ChartAgentContext
)