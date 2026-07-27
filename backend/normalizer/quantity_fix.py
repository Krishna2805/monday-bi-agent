"""
quantity_fix.py — Mixed Quantity Format Parser
================================================

WHY THIS FILE EXISTS:
    The Work Orders board has quantity columns with wildly inconsistent
    formats. Real examples from the data:
    
      "5360 HA"       → 5360.0, unit "HA" (hectares)
      "57.55 HA"      → 57.55, unit "HA"
      "98000 Acres"   → 98000.0, unit "Acres"
      "2 location"    → 2.0, unit "location"
      "NA"            → None, None
      ""              → None, None
      "5360"          → 5360.0, None (no unit)
    
    The numeric part is needed for:
      - Calculating completion percentages (billed qty / PO qty)
      - Identifying large vs small projects
      - Balance quantity reporting
    
    The unit part is useful for:
      - Context in Gemini's explanations ("5360 hectares surveyed")
      - Grouping by measurement type

PARSING STRATEGY:
    We use a regex that splits the string into:
      1. Leading numeric part (integers or decimals, with optional commas)
      2. Everything after the number as the unit
    
    This is intentionally lenient — it extracts what it can and returns
    None for anything unparseable rather than crashing.
"""

import re
from typing import Optional

# Regex pattern explanation:
#   ^                  — start of string
#   ([\d,]+\.?\d*)     — capture group 1: the numeric part
#     [\d,]+           — one or more digits or commas (handles "4,89,360")
#     \.?              — optional decimal point
#     \d*              — optional decimal digits
#   \s*                — optional whitespace between number and unit
#   (.*)               — capture group 2: everything else (the unit)
#   $                  — end of string
QUANTITY_PATTERN = re.compile(r'^([\d,]+\.?\d*)\s*(.*)$')


def parse_quantity(raw) -> dict:
    """
    Parse a mixed quantity string into numeric value and unit.

    Args:
        raw: Raw quantity string from Monday.com (e.g., "5360 HA", "NA", "")

    Returns:
        A dict with three keys:
        {
            "numeric": float or None — the parsed number
            "unit": str or None — the unit label (e.g., "HA", "Acres")
            "raw": str — the original input (for debugging)
        }

    WHY RETURN A DICT NOT A TUPLE:
        Dicts are self-documenting — when you see result["unit"], it's
        clear what you're accessing. Tuples would require remembering
        position: result[1] could be unit or raw, easy to mix up.

    Examples:
        parse_quantity("5360 HA")     → {"numeric": 5360.0, "unit": "HA", "raw": "5360 HA"}
        parse_quantity("57.55 HA")    → {"numeric": 57.55, "unit": "HA", "raw": "57.55 HA"}
        parse_quantity("2 location")  → {"numeric": 2.0, "unit": "location", "raw": "2 location"}
        parse_quantity("NA")          → {"numeric": None, "unit": None, "raw": "NA"}
        parse_quantity("")            → {"numeric": None, "unit": None, "raw": ""}
        parse_quantity(None)          → {"numeric": None, "unit": None, "raw": None}
    """
    # Handle null / empty / explicit "not available" markers
    if not raw or str(raw).strip().upper() in ("NA", "N/A", "", "-"):
        return {"numeric": None, "unit": None, "raw": raw}

    raw_str = str(raw).strip()

    # Try to match the pattern: number followed by optional unit
    match = QUANTITY_PATTERN.match(raw_str)
    if match:
        # Extract numeric part — remove commas before converting
        numeric_str = match.group(1).replace(",", "")
        try:
            numeric = float(numeric_str)
        except ValueError:
            # Shouldn't happen given the regex, but defensive coding
            return {"numeric": None, "unit": None, "raw": raw_str}

        # Extract unit part — strip whitespace, None if empty
        unit = match.group(2).strip() or None

        return {"numeric": numeric, "unit": unit, "raw": raw_str}

    # No match — the string doesn't start with a number
    # This could be something like "Various" or "TBD"
    return {"numeric": None, "unit": None, "raw": raw_str}
