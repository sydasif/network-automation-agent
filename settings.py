# settings.py
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# REPLACED: Database config with Inventory config
INVENTORY_FILE = BASE_DIR / "hosts.yaml"

# ... (Rest of LLM and Timeout settings remain the same)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 2000
DEVICE_TIMEOUT = 30
CACHE_TTL = 300
