"""
config.py — Centralized Environment Configuration
===================================================

WHY THIS FILE EXISTS:
    Every external credential and configurable value lives here.
    No other file in the project imports from os.environ directly.
    This gives us a single place to:
      1. Load .env in development (via python-dotenv)
      2. Validate that all required vars are present at startup
      3. Swap values (e.g., Gemini model) without touching any code

HOW IT WORKS:
    - python-dotenv reads the .env file and populates os.environ
    - We read each variable once and store it as a module-level constant
    - assert statements crash the app immediately at import time if
      any required variable is missing — this is intentional so we
      fail fast rather than getting cryptic errors mid-request

USAGE:
    from config import GOOGLE_API_KEY, GEMINI_MODEL, ...
"""

import os
from dotenv import load_dotenv

# load_dotenv() reads .env from the current working directory (or parent dirs).
# In production (Railway), env vars are set directly — load_dotenv is a no-op.
load_dotenv()

# --- Google Gemini Configuration ---
# GOOGLE_API_KEY: authenticates all calls to the Gemini API.
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# GEMINI_MODEL: allows switching between model variants (e.g., gemini-2.0-flash,
# gemini-2.5-flash) without code changes. This is critical because:
#   - Free-tier rate limits differ by model
#   - We may need to downgrade/upgrade during demos
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "")

# --- Monday.com Configuration ---
# MONDAY_API_TOKEN: Bearer token for Monday.com's GraphQL API.
# Scoped to read-only board access in our use case.
MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")

# Board IDs: Monday.com identifies each board by a numeric ID.
# We need two boards:
#   - WO_BOARD_ID: Work Orders board (project execution, billing, AR)
#   - DEALS_BOARD_ID: Deals Pipeline board (sales funnel, probabilities)
WO_BOARD_ID: str = os.getenv("MONDAY_WO_BOARD_ID", "")
DEALS_BOARD_ID: str = os.getenv("MONDAY_DEALS_BOARD_ID", "")

# --- Startup Validation ---
# We intentionally crash at import time if any required variable is missing.
# This prevents the server from starting in a broken state where it would
# accept requests and then fail with confusing errors when trying to call
# Monday.com or Gemini.
assert GOOGLE_API_KEY, "GOOGLE_API_KEY not set — add it to .env or environment"
assert GEMINI_MODEL, "GEMINI_MODEL not set — add it to .env (e.g., gemini-2.0-flash)"
assert MONDAY_API_TOKEN, "MONDAY_API_TOKEN not set — get it from Monday.com developer settings"
assert WO_BOARD_ID, "MONDAY_WO_BOARD_ID not set — find it in the board URL"
assert DEALS_BOARD_ID, "MONDAY_DEALS_BOARD_ID not set — find it in the board URL"
