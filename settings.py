import os
from pathlib import Path

from dotenv import load_dotenv

# Automatically load .env file from the project root
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent

# Database
DATABASE_NAME = "inventory.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / DATABASE_NAME}")

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 2000

# Network Device Settings
DEVICE_TIMEOUT = 30
CACHE_TTL = 300
