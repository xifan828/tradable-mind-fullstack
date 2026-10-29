"""Application settings and environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment
ENV = os.getenv("ENV", "development")

# API Keys (load from environment variables)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

# Add your configuration here

# Quant agent -----------------------------------------------------------------
# The quant agent runs on an OpenRouter slug and writes its own Python in a
# persistent REPL. Override with QUANT_AGENT_MODEL in backend/.env.
DEFAULT_QUANT_AGENT_MODEL = "deepseek/deepseek-v4.1-flash"


def get_quant_agent_model() -> str:
    """Return the quant agent's OpenRouter model slug (QUANT_AGENT_MODEL)."""
    return os.getenv("QUANT_AGENT_MODEL") or DEFAULT_QUANT_AGENT_MODEL


def get_quant_agent_thinking_level() -> str | None:
    """Return the quant agent's reasoning effort (QUANT_AGENT_THINKING_LEVEL)."""
    return os.getenv("QUANT_AGENT_THINKING_LEVEL") or None


# Chart agent -----------------------------------------------------------------
# The chart agent is a ChatGoogleGenerativeAI model bound to Gemini's native
# `code_execution` tool, so its model is a Gemini model name, not an OpenRouter
# slug. Override with CHART_AGENT_MODEL in backend/.env.
DEFAULT_CHART_AGENT_MODEL = "gemini-3.8-flash"


def get_chart_agent_model() -> str:
    """Return the chart agent's Gemini model name (CHART_AGENT_MODEL)."""
    return os.getenv("CHART_AGENT_MODEL") or DEFAULT_CHART_AGENT_MODEL


def get_chart_agent_thinking_level() -> str | None:
    """Return the optional Gemini 3 thinking level for the chart call, or None."""
    return os.getenv("CHART_AGENT_THINKING_LEVEL") or None


def get_gemini_api_key() -> str:
    """Return the Google API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in backend/.env"
        )
    return key
