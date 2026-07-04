from langchain_google_genai import ChatGoogleGenerativeAI
import os
from langchain_core.messages import BaseMessage, AIMessage
from typing import Literal
from dotenv import load_dotenv
load_dotenv()

gemini_model_map = {
    "2.5_pro": "models/gemini-2.5-pro",
    "2.5_flash": "models/gemini-flash-latest",
    "3_pro": "models/gemini-3-pro-preview",
    "3_flash": "models/gemini-3-flash-preview"
}

async def ainvoke_gemini_model(
    input: str | list[BaseMessage] | list[tuple[str, str]],
    model_type: Literal["2.5_pro", "2.5_flash", "3_pro"],
    **llm_kwargs,
) -> AIMessage:

    if model_type not in gemini_model_map:
        raise ValueError(f"Unsupported model type: {model_type}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")

    llm = ChatGoogleGenerativeAI(
        model=gemini_model_map[model_type],
        api_key=api_key,
        max_retries=0,
        **llm_kwargs,
    )

    return await llm.ainvoke(input)

def invoke_gemini_model(
    input: str | list[BaseMessage] | list[tuple[str, str]],
    model_type: Literal["2.5_pro", "2.5_flash", "3_pro"],
    **llm_kwargs,
) -> AIMessage:

    if model_type not in gemini_model_map:
        raise ValueError(f"Unsupported model type: {model_type}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")

    llm = ChatGoogleGenerativeAI(
        model=gemini_model_map[model_type],
        api_key=api_key,
        max_retries=0,
        **llm_kwargs,
    )

    return llm.invoke(input)


def parse_langchain_ai_message(ai_message: AIMessage) -> str:
    try:
        if isinstance(ai_message.content, list) and ai_message.content and isinstance(ai_message.content[0], dict):
            return ai_message.content[0].get("text", "")
        else:
            return str(ai_message.content)
    except Exception:
        raise RuntimeError("Failed to parse Langchain AIMessage content: {ai_message.content}")
