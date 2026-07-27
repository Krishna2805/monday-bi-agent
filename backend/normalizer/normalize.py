"""
normalize.py — Master Normalization Functions
===============================================

WHY THIS FILE EXISTS:
    This is the SINGLE ENTRY POINT for converting raw Monday.com API
    responses into clean Python dicts. Every other module in the project
    works with the output of these functions — never with raw API data.

    The normalization pipeline for each item:
    
    Raw Monday.com API item
        │
        ├─ Extract column values using column_maps.py
        │   (translates "text0" → "owner_code")
        │
        ├─ Apply type-specific cleaners:
        │   ├─ date_fix.parse_date()    — for date fields
        │   ├─ amount_fix.clean_amount() — for financial fields
        │   └─ quantity_fix.parse_quantity() — for quantity fields
        │
        └─ Apply entity-specific fixes:
            ├─ deals_fix.infer_status() — for deals with missing status
            └─ (header row removal happens after normalization)

DESIGN PRINCIPLE — ONE ITEM IN, ONE DICT OUT:
    normalize_deal() takes one raw API item → returns one clean dict.
    normalize_work_order() takes one raw API item → returns one clean dict.
    
    The caller (tool_handler.py) does:
        normalized = [normalize_deal(item) for item in raw_items]
    
    This makes it easy to test: pass in a sample raw item, check the output.

WHY SEPARATE FROM THE INDIVIDUAL FIXERS:
    date_fix, amount_fix, etc. are pure utility functions that know
    nothing about Monday.com's API structure. This file is the bridge —
    it knows the API response shape AND which fields to apply which
    cleaner to.
"""

import logging
from typing import Any, Optional

from monday.column_maps import DEALS_COLUMN_MAP, WORK_ORDER_COLUMN_MAP
from normalizer.date_fix import parse_date
from normalizer.amount_fix import clean_amount
from normalizer.deals_fix import infer_status

logger = logging.getLogger(__name__)

# ============================================================
# FIELD TYPE DECLARATIONS
# ============================================================
# These sets define which semantic field names should be treated as
# dates vs amounts. This determines which cleaner function is applied.
#
# WHY SETS INSTEAD OF DECORATORS/CONFIG:
#   Simple, readable, and easily extensible. If you add a new date
#   column to column_maps.py, just add its semantic name here.

# Fields that contain date values (will be run through parse_date)
DEAL_DATE_FIELDS = {
    "close_date_actual",
    "tentative_close_date",
    "created_date",
}

WO_DATE_FIELDS = {
    "data_delivery_date",
    "po_date",
    "probable_start_date",
    "probable_end_date",
    "last_invoice_date",
    "collection_date",
}

# Fields that contain financial amounts (will be run through clean_amount)
DEAL_AMOUNT_FIELDS = {
    "deal_value",
}

WO_AMOUNT_FIELDS = {
    "amount_excl_gst",
    "amount_incl_gst",
    "billed_excl_gst",
    "billed_incl_gst",
    "collected_incl_gst",
    "amount_to_bill_excl_gst",
    "amount_to_bill_incl_gst",
    "amount_receivable",
}


def _extract_column_values(
    raw_item: dict,
    column_map: dict[str, str]
) -> dict[str, Any]:
    """
    Convert raw Monday.com column_values into a flat dict using a column map.

    Monday.com's API returns column values as a list of dicts:
    [
        {"id": "text0", "text": "OWNER_001", "value": "..."},
        {"id": "status4", "text": "Open", "value": "..."},
        ...
    ]

    We convert this into:
    {
        "owner_code": "OWNER_001",
        "deal_status": "Open",
        ...
    }

    Args:
        raw_item: A single item dict from Monday.com's API response.
                  Must have "name" and "column_values" keys.
        column_map: The appropriate column map (DEALS or WORK_ORDER)

    Returns:
        A flat dict with semantic field names as keys and cell text as values.

    HOW IT WORKS:
        1. Build a lookup dict from column_values: {column_id: text_value}
        2. For each entry in the column map, look up the column_id
        3. If found, add the semantic_name → text_value to the result
        4. If not found, log a warning (column might have been deleted)
    """
    # Build lookup: column_id → text value
    # We use "text" not "value" because "text" is the human-readable
    # representation, while "value" is a JSON-encoded structure that
    # varies by column type and is harder to parse consistently.
    col_lookup: dict[str, str] = {}
    for col in raw_item.get("column_values", []):
        col_lookup[col["id"]] = col.get("text", "")

    # Map column IDs to semantic names
    result: dict[str, Any] = {}
    for monday_id, semantic_name in column_map.items():
        if monday_id in col_lookup:
            result[semantic_name] = col_lookup[monday_id]
        # If the column ID isn't in the response, we skip it silently.
        # This handles the case where column_maps.py has placeholder IDs
        # that haven't been updated yet, or columns that were removed.

    return result


def normalize_deal(raw_item: dict) -> dict:
    """
    Normalize a single raw deal item from Monday.com's API.

    The output dict is the ONLY format the analytics layer works with.
    Every deal flowing through the system passes through this function.

    Args:
        raw_item: A single deal item from get_all_items().
                  Shape: {"id": "123", "name": "Naruto", "column_values": [...]}

    Returns:
        A clean dict with all fields normalized:
        {
            "deal_name": "Naruto",
            "owner_code": "OWNER_001",
            "deal_status": "Open",              # inferred if missing
            "deal_value": 489360.0,             # cleaned amount or None
            "probability": "High",
            "tentative_close_date": "2026-02-26", # parsed date or None
            "deal_stage": "B. Sales Qualified Leads",
            "sector": "Mining",
            ...
        }

    PROCESSING STEPS:
        1. Extract the item name (deal name from row title)
        2. Map column IDs to semantic names via column map
        3. Clean date fields through parse_date()
        4. Clean amount fields through clean_amount()
        5. Infer missing deal_status from deal_stage
    """
    # Step 1: Item name is separate from column_values in the API response
    result = {"deal_name": raw_item.get("name", "")}

    # Step 2: Extract and map column values
    fields = _extract_column_values(raw_item, DEALS_COLUMN_MAP)
    result.update(fields)

    # Step 3: Clean date fields
    for field_name in DEAL_DATE_FIELDS:
        if field_name in result:
            result[field_name] = parse_date(result[field_name])

    # Step 4: Clean amount fields
    for field_name in DEAL_AMOUNT_FIELDS:
        if field_name in result:
            result[field_name] = clean_amount(result[field_name])

    # Step 5: Infer missing status from stage
    result["deal_status"] = infer_status(result)

    return result


def normalize_work_order(raw_item: dict) -> dict:
    """
    Normalize a single raw work order item from Monday.com's API.

    Similar to normalize_deal() but for the Work Orders board, which
    has many more columns (38 vs 12) and different data quality issues.

    Args:
        raw_item: A single work order item from get_all_items().
                  Shape: {"id": "456", "name": "Scooby-Doo", "column_values": [...]}

    Returns:
        A clean dict with all fields normalized:
        {
            "wo_name": "Scooby-Doo",
            "customer_name_code": "WOCOMPANY_002",
            "execution_status": "Completed",
            "sector": "Mining",
            "amount_excl_gst": 264398.08,       # cleaned or None
            "billed_excl_gst": None,             # None, NOT 0
            "po_date": "2025-10-29",             # parsed date or None
            "_had_placeholder_amount": False,     # flag for data quality
            ...
        }

    PROCESSING STEPS:
        1. Extract item name (work order name from row title)
        2. Map column IDs to semantic names via column map
        3. Clean date fields
        4. Clean amount fields (with placeholder tracking)
        5. No status inference needed (WO statuses are always filled)
    """
    # Step 1: Item name
    result = {"wo_name": raw_item.get("name", "")}

    # Step 2: Extract and map column values
    fields = _extract_column_values(raw_item, WORK_ORDER_COLUMN_MAP)
    result.update(fields)

    # Step 3: Clean date fields
    for field_name in WO_DATE_FIELDS:
        if field_name in result:
            result[field_name] = parse_date(result[field_name])

    # Step 4: Clean amount fields with placeholder tracking
    # We track whether ANY amount in this WO was a placeholder,
    # so the analytics layer can count and report these.
    had_placeholder = False
    for field_name in WO_AMOUNT_FIELDS:
        if field_name in result:
            raw_val = result[field_name]
            cleaned = clean_amount(raw_val)
            # If raw value was a number but cleaned to None, it was a placeholder
            if cleaned is None and raw_val is not None:
                try:
                    float(str(raw_val).replace(",", ""))
                    had_placeholder = True
                except (ValueError, TypeError):
                    pass
            result[field_name] = cleaned

    result["_had_placeholder_amount"] = had_placeholder

    return result


def format_deal_record(deal: dict) -> dict:
    """
    Format a normalized deal dict for the "records" output format.

    When output_format="records" is requested (e.g., "list all high
    probability deals"), we return individual deal records. This function
    selects the most relevant fields and creates a compact representation.

    Args:
        deal: A normalized deal dict (output of normalize_deal())

    Returns:
        A compact dict with key deal fields for display.

    WHY NOT RETURN THE FULL DICT:
        The full normalized dict has internal fields (like raw values)
        that would bloat the prompt and waste tokens. We curate the fields
        that are actually useful for business conversations.
    """
    return {
        "deal_name": deal.get("deal_name", ""),
        "sector": deal.get("sector", ""),
        "deal_status": deal.get("deal_status", ""),
        "probability": deal.get("probability", ""),
        "deal_value": deal.get("deal_value"),
        "deal_stage": deal.get("deal_stage", ""),
        "tentative_close_date": deal.get("tentative_close_date"),
    }


def format_wo_record(wo: dict) -> dict:
    """
    Format a normalized work order dict for the "records" output format.

    Similar to format_deal_record() but for work orders.

    Args:
        wo: A normalized work order dict (output of normalize_work_order())

    Returns:
        A compact dict with key work order fields for display.
    """
    return {
        "wo_name": wo.get("wo_name", ""),
        "customer_name_code": wo.get("customer_name_code", ""),
        "sector": wo.get("sector", ""),
        "execution_status": wo.get("execution_status", ""),
        "contract_type": wo.get("contract_type", ""),
        "work_type": wo.get("work_type", ""),
        "amount_excl_gst": wo.get("amount_excl_gst"),
        "billed_excl_gst": wo.get("billed_excl_gst"),
        "collected_incl_gst": wo.get("collected_incl_gst"),
        "amount_receivable": wo.get("amount_receivable"),
        "billing_status": wo.get("billing_status", ""),
    }
