import os
from pathlib import Path

from dotenv import load_dotenv

# Automatically load .env file from the project root
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
INVENTORY_FILE = BASE_DIR / "hosts.yaml"

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
LLM_TEMPERATURE = 0.2

# KISS: Simple message count limit instead of token counting
MAX_HISTORY_MESSAGES = 20

# Network Device Settings
DEVICE_TIMEOUT = 30
