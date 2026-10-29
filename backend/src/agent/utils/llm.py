import logging
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

openrouter_model_map = {
    "deepseek": "deepseek/deepseek-v4.1-flash",
    "gemini": "google/gemini-3.8-flash",
    "kimi": "moonshotai/kimi-k3",
    "glm": "z-ai/glm-5.3-flashx",
}

# How much thinking the model may spend before answering. OpenRouter normalizes
# this across providers as `reasoning.effort`; Gemini 3 maps it straight onto
# Google's `thinkingLevel`. Models that don't support a given level get the
# nearest one instead, and non-reasoning models ignore the field entirely, so
# the value is safe to send to every model in the roster.
ReasoningEffort = Literal["low", "medium", "high"]
REASONING_EFFORTS: tuple[ReasoningEffort, ...] = ("low", "medium", "high")
DEFAULT_REASONING_EFFORT: ReasoningEffort = "medium"


def resolve_reasoning_effort(reasoning_effort: str | None) -> ReasoningEffort:
    """Normalize a requested effort level, defaulting to `medium`.

    Callers may not specify one at all (the CLI and older clients), and the
    frontend persists the choice in localStorage so a stale value can outlive a
    roster change. Neither should fail a run, so anything unrecognized falls
    back to the default instead of raising.
    """
    if not reasoning_effort:
        return DEFAULT_REASONING_EFFORT
    if reasoning_effort not in REASONING_EFFORTS:
        logger.warning(
            "Unknown reasoning effort %r; using %r instead",
            reasoning_effort,
            DEFAULT_REASONING_EFFORT,
        )
        return DEFAULT_REASONING_EFFORT
    return reasoning_effort


def build_openrouter_model(
    model_name: str,
    reasoning_effort: str | None = None,
    **llm_kwargs,
) -> ChatOpenAI:
    """Build a ChatOpenAI client pointed at the OpenRouter API.

    The key is never passed in: it always comes from the OPENROUTER_API_KEY
    environment variable (see backend/.env).

    Args:
        model_name: OpenRouter model slug, e.g. "google/gemini-3-flash-preview".
        reasoning_effort: "low", "medium" or "high". Defaults to "medium" when
            omitted; there is no way to send no reasoning config at all.
        **llm_kwargs: Extra kwargs forwarded to ChatOpenAI (temperature, etc.).
            An `extra_body` is merged rather than replaced, so the reasoning
            config survives a caller passing its own.
    """
    # A caller-supplied key would be ignored, so drop it rather than let
    # ChatOpenAI raise a confusing duplicate-kwarg TypeError.
    llm_kwargs.pop("api_key", None)

    resolved_key = os.getenv("OPENROUTER_API_KEY")
    if not resolved_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    # OpenRouter reads the normalized shape `reasoning: {"effort": ...}`; the
    # OpenAI-style top-level `reasoning_effort` is not what its gateway expects.
    extra_body = dict(llm_kwargs.pop("extra_body", None) or {})
    extra_body["reasoning"] = {
        "effort": resolve_reasoning_effort(reasoning_effort),
    }

    return ChatOpenAI(
        model=model_name,
        api_key=resolved_key,
        base_url="https://openrouter.ai/api/v1",
        # The OpenAI SDK retries connection errors, timeouts and 429/5xx with its
        # own backoff (honouring Retry-After). At 0 a single transient TLS
        # failure failed the whole run, so keep the SDK's default budget of 2.
        # Non-retryable errors (401/400) are still raised immediately.
        max_retries=2,
        extra_body=extra_body,
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
    """Return the message's text content as a plain string.

    OpenAI-compatible providers return `content` as a string, but Gemini 3
    returns a list of content blocks (text, native tool calls, generated
    images), so `str(content)` would dump the whole list — base64 images
    included — instead of the answer. `AIMessage.text` joins the text blocks in
    both cases.
    """
    return ai_message.text.strip()
