"""
amount_fix.py — Financial Amount Cleaning and Safe Aggregation
===============================================================

WHY THIS FILE EXISTS:
    The Work Orders board has several financial columns (PO amount,
    billed, collected, AR, etc.) that contain messy values:
    
    1. PLACEHOLDER VALUES (1.2332, 1.455176):
       Monday.com or the data import process inserted these specific
       decimal values for rows where the amount is intentionally empty
       (e.g., Proof of Concept deals or "Not Billable" entries).
       If we treat these as real amounts, our revenue totals would be
       wrong. We detect and convert them to None.
    
    2. EMPTY / NULL VALUES:
       Some rows have genuinely missing amounts (empty cells, None).
       We must distinguish "not yet entered" from "zero" because:
       - A work order with missing billed amount ≠ ₹0 billed
       - Summing None as 0 would undercount missing data
       - We need to report HOW MANY values are missing (data quality)
    
    3. COMMA-SEPARATED NUMBERS:
       Large Indian currency values sometimes use commas (e.g.,
       "4,89,360" or "489,360"). We strip commas before parsing.

    4. STRING VALUES:
       Some amount fields contain text like "NA", "Not Billable",
       or empty strings. These should become None, not crash.

DESIGN PRINCIPLE — NULLS ARE NOT ZEROS:
    Throughout this codebase, we NEVER silently convert None to 0.
    The safe_sum() function returns both the total AND the count of
    null values, so the caller can decide whether to proceed with
    a partial sum or flag it as a data quality issue.
"""

from typing import Optional

# ============================================================
# PLACEHOLDER DETECTION
# ============================================================
# These exact decimal values appear in the source data as system
# defaults for POC and Not Billable entries. They are NOT real
# financial amounts. We use a set for O(1) lookup.
#
# HOW WE IDENTIFIED THESE:
#   During the data audit, we noticed that several POC rows had
#   amounts of exactly 1.2332 and 1.455176 — suspiciously precise
#   non-round numbers that appear across multiple unrelated rows.
#   These are system-injected defaults, not actual contract values.
PLACEHOLDER_VALUES = {1.2332, 1.455176}

# Tolerance for floating point comparison. We compare with a small
# epsilon because floating point arithmetic can introduce tiny errors
# (e.g., 1.2332 might be stored as 1.2331999999999998).
PLACEHOLDER_TOLERANCE = 0.0001


def _is_placeholder(value: float) -> bool:
    """
    Check if a numeric value is a known placeholder.

    Uses approximate comparison instead of exact equality because
    floating point numbers can have tiny rounding errors.

    Args:
        value: The numeric value to check

    Returns:
        True if the value matches a known placeholder (within tolerance)
    """
    return any(
        abs(value - p) < PLACEHOLDER_TOLERANCE
        for p in PLACEHOLDER_VALUES
    )


def clean_amount(value) -> Optional[float]:
    """
    Clean a raw financial value into a float or None.

    Processing pipeline:
      1. None / empty / "NA" → None
      2. Strip commas (Indian number format: 4,89,360)
      3. Parse to float
      4. Check against placeholder values → None if placeholder
      5. Return the cleaned float

    Args:
        value: Raw amount from Monday.com (could be number, string,
               None, or anything)

    Returns:
        Cleaned float value, or None if the value is:
        - Missing (None, empty, "NA")
        - A known placeholder (1.2332, 1.455176)
        - Unparseable (random text)

    WHY RETURN None INSTEAD OF 0:
        Returning 0 would mean "this amount is confirmed to be zero",
        which is different from "this amount is unknown/missing".
        When we sum amounts later, we need to know how many values
        were missing so we can report it as a data quality caveat.
    """
    # Handle None and empty values
    if value is None:
        return None

    str_value = str(value).strip()
    if str_value == "" or str_value.upper() in ("NA", "N/A", "NOT BILLABLE", "-"):
        return None

    try:
        # Remove commas (handles both "489,360" and "4,89,360" Indian format)
        cleaned = str_value.replace(",", "")
        amount = float(cleaned)

        # Check for placeholder values
        if _is_placeholder(amount):
            return None

        return amount

    except (ValueError, TypeError):
        # Value is something we can't parse as a number (e.g., "TBD")
        return None


def safe_sum(values: list[Optional[float]]) -> tuple[float, int]:
    """
    Sum a list of values, tracking how many are null.

    This is the ONLY way financial values should be summed in this
    codebase. It separates "the sum of known values" from "how many
    values are missing" so callers can make informed decisions.

    Args:
        values: List of cleaned amounts (floats and Nones)

    Returns:
        Tuple of (sum_of_non_null_values, count_of_null_values)

    Examples:
        safe_sum([100, 200, None, 300]) → (600.0, 1)
        safe_sum([None, None]) → (0.0, 2)
        safe_sum([100, 200, 300]) → (600.0, 0)

    WHY NOT JUST USE sum():
        sum([100, None, 200]) crashes with TypeError.
        sum([v for v in values if v]) silently drops zeros AND Nones.
        sum([v or 0 for v in values]) silently converts None to 0.
        
        All of these lose information. Our approach preserves the
        count of missing values so analytics can report:
        "Pipeline total: ₹4.5Cr (⚠️ 3 deals missing values)"
    """
    non_null = [v for v in values if v is not None]
    null_count = len(values) - len(non_null)
    return (sum(non_null), null_count)
