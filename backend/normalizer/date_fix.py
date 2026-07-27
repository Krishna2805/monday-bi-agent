"""
date_fix.py — Date Parsing and Normalization
=============================================

WHY THIS FILE EXISTS:
    Monday.com dates can arrive in multiple formats depending on how
    the board was set up and how data was imported:
    
    1. Excel serial integers (e.g., 45757)
       - This happens when data is bulk-imported from Excel
       - Excel stores dates as "days since epoch" where the epoch
         is 1899-12-30 (NOT 1900-01-01 due to a historical bug —
         Lotus 1-2-3 incorrectly treated 1900 as a leap year, and
         Excel preserved this for backwards compatibility)
    
    2. ISO-format strings (e.g., "2025-09-27" or "2025-09-27 00:00:00")
       - This is what Monday.com's native date columns produce
    
    3. Empty / null / garbage values
       - Missing dates, "NA", blank strings

    This module handles ALL of these cases and normalizes them to
    a consistent "YYYY-MM-DD" string format (or None if unparseable).
    
    The rest of the codebase ONLY sees clean "YYYY-MM-DD" strings
    or None — never raw integers or mixed formats.

EXCEL SERIAL DATE EXPLANATION (for interviews):
    Excel represents dates as the number of days since December 30, 1899.
    Why December 30 and not January 1?
    
    Lotus 1-2-3 (the original spreadsheet) incorrectly assumed 1900 was
    a leap year (it's not — century years must be divisible by 400).
    When Microsoft built Excel, they copied this bug intentionally so that
    Excel files would be compatible with Lotus 1-2-3 files. The result is
    that Excel's "day 1" is January 1, 1900, but the epoch for correct
    math is December 30, 1899 (two days earlier to compensate for the
    off-by-one error and the phantom Feb 29, 1900).
"""

from datetime import datetime, timedelta
from typing import Optional

# Excel epoch — the reference point for serial date calculations.
# See module docstring for why this is Dec 30, not Jan 1.
EXCEL_EPOCH = datetime(1899, 12, 30)

# Valid serial date range. Excel serial 1000 ≈ September 1902.
# Any serial below this is likely a garbage value (e.g., a small
# integer that got misinterpreted). We also cap at 60000 which is
# approximately year 2064 — anything beyond is suspicious.
MIN_VALID_SERIAL = 1000
MAX_VALID_SERIAL = 60000


def parse_date(value) -> Optional[str]:
    """
    Convert any date representation to a clean "YYYY-MM-DD" string.

    Handles:
      - Excel serial integers: 45757 → "2025-04-12"
      - ISO strings: "2025-09-27" → "2025-09-27"
      - Datetime strings: "2025-09-27 00:00:00" → "2025-09-27"
      - None / empty / "NA" → None

    Args:
        value: Raw date value from Monday.com (could be int, float,
               string, None, or anything)

    Returns:
        "YYYY-MM-DD" string or None if the value can't be parsed.

    WHY RETURN STRINGS NOT datetime OBJECTS:
        Our analytics functions compare dates as strings and pass them
        to the LLM in JSON. Keeping them as "YYYY-MM-DD" strings means:
        - They sort correctly as strings (lexicographic = chronological)
        - JSON-serializable without custom encoders
        - Easy to debug (you can read them directly)
    """
    # Handle None, empty strings, and explicit "not available" markers
    if value is None:
        return None

    str_value = str(value).strip()
    if str_value == "" or str_value.upper() in ("NA", "N/A", "NONE"):
        return None

    # --- Attempt 1: ISO-format string (most common from Monday.com) ---
    # Try parsing "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" formats
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str_value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # --- Attempt 2: Excel serial integer ---
    # If the string looks like a number, try converting from Excel serial
    try:
        serial = int(float(str_value))
        if MIN_VALID_SERIAL <= serial <= MAX_VALID_SERIAL:
            result = EXCEL_EPOCH + timedelta(days=serial)
            return result.strftime("%Y-%m-%d")
        else:
            # Number is outside valid date range — treat as garbage
            return None
    except (ValueError, TypeError, OverflowError):
        pass

    # --- Attempt 3: Other common date formats ---
    # Monday.com sometimes returns dates in DD/MM/YYYY or MM/DD/YYYY
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str_value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If nothing worked, return None rather than crashing
    return None


def is_date_in_range(date_str: Optional[str], start: str, end: str) -> bool:
    """
    Check if a YYYY-MM-DD date string falls within a range (inclusive).

    Args:
        date_str: The date to check (or None)
        start: Range start in "YYYY-MM-DD" format
        end: Range end in "YYYY-MM-DD" format

    Returns:
        True if start <= date_str <= end, False otherwise.
        Returns False if date_str is None.

    WHY THIS EXISTS:
        Used by deal/WO filters for queries like "deals closing this month"
        or "work orders started after January". String comparison works
        because YYYY-MM-DD format sorts lexicographically.
    """
    if not date_str:
        return False
    return start <= date_str <= end
