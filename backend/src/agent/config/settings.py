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
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

# Add your configuration here
