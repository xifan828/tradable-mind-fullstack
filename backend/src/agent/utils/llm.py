import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

load_dotenv()

openrouter_model_map = {
    "deepseek": "deepseek/deepseek-v4.1-flash",
    "gemini": "google/gemini-3.8-flash",
    "kimi": "moonshotai/kimi-k3",
    "glm": "z-ai/glm-5.3-flashx",
}


def build_openrouter_model(
    model_name: str,
    api_key: str | None = None,
    **llm_kwargs,
) -> ChatOpenAI:
    """Build a ChatOpenAI client pointed at the OpenRouter API.

    Args:
        model_name: OpenRouter model slug, e.g. "google/gemini-3-flash-preview".
        api_key: OpenRouter API key; falls back to the OPENROUTER_API_KEY
            environment variable when omitted.
        **llm_kwargs: Extra kwargs forwarded to ChatOpenAI (temperature, etc.).
    """
    resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not resolved_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    return ChatOpenAI(
        model=model_name,
        api_key=resolved_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        **llm_kwargs,
    )


async def ainvoke_model(
    input: str | list[BaseMessage] | list[tuple[str, str]],
    model_type: Literal["deepseek", "gemini", "kimi", "glm"],
    **llm_kwargs,
) -> AIMessage:
    if model_type not in openrouter_model_map:
        raise ValueError(f"Unsupported model type: {model_type}")
    llm = build_openrouter_model(openrouter_model_map[model_type], **llm_kwargs)
    return await llm.ainvoke(input)


def invoke_model(
    input: str | list[BaseMessage] | list[tuple[str, str]],
    model_type: Literal["deepseek", "gemini", "kimi", "glm"],
    **llm_kwargs,
) -> AIMessage:
    if model_type not in openrouter_model_map:
        raise ValueError(f"Unsupported model type: {model_type}")
    llm = build_openrouter_model(openrouter_model_map[model_type], **llm_kwargs)
    return llm.invoke(input)


def parse_langchain_ai_message(ai_message: AIMessage) -> str:
    """Return the message content as a plain string (OpenAI-compatible shape)."""
    return str(ai_message.content)
