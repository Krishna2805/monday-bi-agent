"""
config.py — Centralized Environment Configuration
===================================================

WHY THIS FILE EXISTS:
    Every external credential and configurable value lives here.
    No other file in the project imports from os.environ directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Groq LLM API Configuration ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# --- Monday.com Configuration ---
MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")
WO_BOARD_ID: str = os.getenv("MONDAY_WO_BOARD_ID", "")
DEALS_BOARD_ID: str = os.getenv("MONDAY_DEALS_BOARD_ID", "")

# --- Startup Validation ---
assert GROQ_API_KEY, "GROQ_API_KEY not set — add it to .env or environment"
assert MONDAY_API_TOKEN, "MONDAY_API_TOKEN not set — get it from Monday.com developer settings"
assert WO_BOARD_ID, "MONDAY_WO_BOARD_ID not set — add numeric ID from Monday.com board URL"
assert DEALS_BOARD_ID, "MONDAY_DEALS_BOARD_ID not set — add numeric ID from Monday.com board URL"
