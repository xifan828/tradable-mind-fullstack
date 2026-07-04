from langchain.tools import tool

from agent.prompts.technical_analysis import THINK_TOOL_DESCRIPTION

@tool(description=THINK_TOOL_DESCRIPTION, parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded."