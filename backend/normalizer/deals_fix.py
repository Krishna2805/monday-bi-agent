"""
deals_fix.py — Deal-Specific Data Quality Fixes
=================================================

WHY THIS FILE EXISTS:
    The Deals Pipeline board has two specific data quality issues that
    are unique to this board (not shared with Work Orders):
    
    1. EMBEDDED HEADER ROW:
       The deals data contains a row where the deal name is "Nezuko"
       but the column values contain header text like "Deal Status",
       "Closure Probability", "Deal Stage", etc. This is a repeated
       header row that was accidentally included as data during the
       Excel import.
       
       If we don't filter this out:
       - It gets counted as an Open deal (inflating deal count)
       - Its "amount" would be a text string (crashing aggregation)
       - Analytics results would be subtly wrong
    
    2. MISSING DEAL STATUS:
       At least one row has an empty deal_status field. Since our
       analytics group deals by status (Open, Won, Dead), a blank
       status would create an "Unknown" category or cause key errors.
       
       We infer the status from the deal_stage:
       - Early stages (A, B, C) → likely "Open"
       - Won stage → "Won"
       - Dead/Not relevant → "Dead"
       - If we can't infer → "Unknown" (we never silently assume)

WHEN THESE FIXES ARE APPLIED:
    These run AFTER the master normalizer converts raw Monday.com
    items into clean Python dicts. The flow is:
    
    raw Monday.com item → normalize_deal() → deals_fix functions → clean dict
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# HEADER ROW DETECTION
# ============================================================
# These are column header texts that should never appear as actual
# cell values. If a row's deal_status or deal_stage contains one
# of these strings, it's an embedded header row — not real data.
#
# We check multiple fields because the header row might have "Deal
# Status" in the status column AND "Closure Probability" in the
# probability column. Any ONE match is enough to flag the row.
HEADER_INDICATORS = {
    "Deal Status",
    "Closure Probability",
    "Deal Stage",
    "Sector/service",
    "Owner code",
    "Client Code",
    "Product deal",
    "Close Date (A)",
    "Tentative Close Date",
    "Created Date",
    "Masked Deal value",
}


def drop_header_rows(items: list[dict]) -> list[dict]:
    """
    Remove embedded header rows from the normalized deals list.

    An embedded header row is a data row that contains column header
    text in its value fields (e.g., deal_status = "Deal Status").
    This happens when Excel data with repeated headers is imported.

    Args:
        items: List of normalized deal dicts (after normalize_deal())

    Returns:
        Filtered list with header rows removed.

    WHY NOT FILTER BY DEAL NAME ("Nezuko"):
        Filtering by a specific name is fragile — if the data changes
        or a new export has a different placeholder name, the filter
        breaks. Instead, we check the CONTENT of multiple fields for
        header text, which is more robust.
    """
    original_count = len(items)
    cleaned = []

    for item in items:
        # Check if any field contains a header indicator string
        fields_to_check = [
            item.get("deal_status", ""),
            item.get("probability", ""),
            item.get("deal_stage", ""),
            item.get("sector", ""),
            item.get("owner_code", ""),
        ]

        is_header = any(
            str(field).strip() in HEADER_INDICATORS
            for field in fields_to_check
            if field  # Skip None / empty fields
        )

        if is_header:
            logger.info(
                f"Dropped embedded header row: "
                f"deal_name='{item.get('deal_name', '?')}'"
            )
        else:
            cleaned.append(item)

    dropped = original_count - len(cleaned)
    if dropped > 0:
        logger.info(f"Dropped {dropped} embedded header row(s) from deals data")

    return cleaned


# ============================================================
# DEAL STAGE → STATUS MAPPING
# ============================================================
# Monday.com Deal Stages go from A (earliest) to N (not relevant).
# The stage letter tells us approximately where a deal is in the
# sales funnel. If the deal_status is missing, we can infer it
# from the stage.
#
# Early stages (A-J) = deal is still being worked → "Open"
# Won stage = deal was closed successfully → "Won"
# Dead/Not relevant = deal was abandoned → "Dead"
STAGE_STATUS_MAP = {
    "A": "Open",   # A. Lead Generated
    "B": "Open",   # B. Sales Qualified Leads
    "C": "Open",   # C. Initial discussion
    "D": "Open",   # D. NDA signed
    "E": "Open",   # E. Demo Done
    "F": "Open",   # F. Proposal Sent
    "G": "Open",   # G. In Negotiations
    "H": "Open",   # H. Verbal Confirmation
    "I": "Open",   # I. PO Received
    "J": "Open",   # J. Partially won
    "K": "Won",    # K. Won (fully closed)
    "L": "Dead",   # L. Dead
    "M": "Dead",   # M. On Hold (treated as Dead for analytics)
    "N": "Dead",   # N. Not relevant
}


def infer_status(item: dict) -> str:
    """
    Infer deal_status from deal_stage when status is missing.

    Args:
        item: A normalized deal dict that may have empty deal_status

    Returns:
        The existing status if present, otherwise an inferred status
        based on the deal_stage letter. Returns "Unknown" if neither
        status nor stage provides enough information.

    HOW IT WORKS:
        1. If deal_status is already filled → return it as-is
        2. Extract the first letter of deal_stage (e.g., "B" from
           "B. Sales Qualified Leads")
        3. Look up the letter in STAGE_STATUS_MAP
        4. If no match → return "Unknown" (never guess silently)

    WHY NOT DEFAULT TO "Open":
        Defaulting to "Open" would inflate the open deal count.
        "Unknown" is honest — it tells the analytics layer and
        ultimately the user that we have incomplete data.
    """
    status = item.get("deal_status", "").strip()
    if status:
        return status

    # Try to infer from stage
    stage = item.get("deal_stage", "").strip()
    if stage:
        # Extract the first letter (e.g., "B" from "B. Sales Qualified Leads")
        stage_letter = stage[0].upper()
        inferred = STAGE_STATUS_MAP.get(stage_letter)
        if inferred:
            logger.debug(
                f"Inferred deal_status='{inferred}' from "
                f"deal_stage='{stage}' for deal '{item.get('deal_name', '?')}'"
            )
            return inferred

    return "Unknown"
