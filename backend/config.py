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
import logging

_logger = logging.getLogger(__name__)

missing_keys = []
if not GROQ_API_KEY:
    missing_keys.append("GROQ_API_KEY")
if not MONDAY_API_TOKEN:
    missing_keys.append("MONDAY_API_TOKEN")
if not WO_BOARD_ID:
    missing_keys.append("MONDAY_WO_BOARD_ID")
if not DEALS_BOARD_ID:
    missing_keys.append("MONDAY_DEALS_BOARD_ID")

if missing_keys:
    _logger.warning(
        f"Missing configuration keys: {', '.join(missing_keys)}. "
        "Populate backend/.env or set system environment variables before invoking live endpoints."
    )
