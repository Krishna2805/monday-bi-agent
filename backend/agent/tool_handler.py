"""
tool_handler.py — Tool Call Dispatcher & Internal Analytics Chaining
=====================================================================

WHY THIS FILE EXISTS:
    This is the CENTRAL NERVOUS SYSTEM of the backend. When the LLM Agent
    decides to call a tool (e.g., query_deals), this module:

      1. Fetches raw data from Monday.com (via MondayClient)
      2. Normalizes every item (via normalize_deal / normalize_work_order)
      3. Applies filters from tool parameters (sector, status, etc.)
      4. Routes to the correct output:
         - "summary" → chains analytics functions internally
         - "records" → returns formatted individual rows

    The LLM NEVER calls analytics functions directly. This module
    handles that internally. The LLM only sees 2 tools; Python does
    the rest.

THE INTERNAL CHAINING PATTERN:
    This is the key architectural decision. Instead of:
    
        LLM → query_deals() → raw data
        LLM → compute_pipeline_metrics() → aggregated data
        (LLM decides which to call and in what order)
    
    We do:
    
        LLM → query_deals()
        Python internally → fetch → normalize → filter → compute_pipeline_summary()
        Return → aggregated summary JSON
    
    Benefits:
    - LLM makes ONE decision (which board), not two (which board + what to compute)
    - Analytics functions stay standalone and testable
    - No risk of LLM calling compute without calling query first

FILTER APPLICATION:
    The LLM passes filter parameters (sector, deal_status, probability, etc.)
    extracted from the user's question. We apply these as AND filters:
    if sector="Mining" AND deal_status="Open", only Mining + Open items pass.

    Parameters omitted (None) are not filtered — meaning
    "no filter on this dimension". This is handled by apply_filters()
    in aggregator.py.
"""

import logging
from typing import Any

from monday.client import MondayClient
from normalizer.normalize import (
    normalize_deal,
    normalize_work_order,
    format_deal_record,
    format_wo_record,
)
from normalizer.deals_fix import drop_header_rows
from analytics.pipeline import compute_pipeline_summary
from analytics.revenue import compute_revenue_summary
from analytics.aggregator import apply_filters, extract_deal_caveats, extract_wo_caveats
from config import WO_BOARD_ID, DEALS_BOARD_ID

logger = logging.getLogger(__name__)

# Single client instance — reused across all tool calls.
# This is safe because MondayClient is stateless (it only holds
# headers, and creates a new httpx.AsyncClient per request).
monday = MondayClient()


# ============================================================
# FILTER KEY MAPPINGS
# ============================================================
# These map tool parameter names to normalized dict field names.
# E.g., parameter {"sector": "Mining"} filters on the "sector" key in dicts.
#
# We keep these as explicit lists rather than assuming the names
# match, because they might diverge in the future.

DEAL_FILTER_KEYS = ["sector", "deal_status", "probability"]
WO_FILTER_KEYS = ["sector", "execution_status", "contract_type"]


async def handle_tool_call(tool_name: str, tool_input: dict[str, Any]) -> dict:
    """
    Dispatch a tool call to the appropriate data pipeline.

    This is the function passed to the LLM agent loop. When the agent
    requires data retrieval, the agent loop calls this with the tool
    name and parameters.

    Args:
        tool_name: "query_deals" or "query_work_orders"
        tool_input: Parameters from tool call, e.g.:
                    {"sector": "Mining", "output_format": "summary"}

    Returns:
        A dict containing either:
        - Aggregated KPI summary (if output_format="summary")
        - List of formatted records (if output_format="records")
        - Error dict with data_quality_notes (if something fails)

    THE COMPLETE PIPELINE FOR query_deals (output_format="summary"):
        1. monday.get_all_items(DEALS_BOARD_ID) → raw API items
        2. [normalize_deal(i) for i in raw] → clean dicts
        3. drop_header_rows() → remove embedded Excel headers
        4. apply_filters(deals, {sector, status, prob}) → filtered list
        5. compute_pipeline_summary(filtered) → KPI summary JSON
        6. Return summary to LLM for natural language explanation

    THE COMPLETE PIPELINE FOR query_deals (output_format="records"):
        Steps 1-4 same as above
        5. [format_deal_record(d) for d in filtered[:50]] → compact rows
        6. Return records list to LLM for listing
    """
    try:
        # Extract output format — defaults to "summary" if not provided
        output_format = tool_input.get("output_format", "summary")

        if tool_name == "query_deals":
            return await _handle_deals(tool_input, output_format)

        elif tool_name == "query_work_orders":
            return await _handle_work_orders(tool_input, output_format)

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    except Exception as e:
        logger.error(f"Tool call failed: {tool_name} — {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "tool": tool_name,
            "data_quality_notes": [f"Tool execution failed: {str(e)}"]
        }


async def _handle_deals(
    tool_input: dict[str, Any],
    output_format: str
) -> dict:
    """
    Internal handler for query_deals tool calls.

    Separated from handle_tool_call for clarity and testability.
    This function encapsulates the entire deals data pipeline.

    Args:
        tool_input: Tool parameters
        output_format: "summary" or "records"

    Returns:
        Summary dict or records dict
    """
    logger.info(f"Handling query_deals: filters={tool_input}, format={output_format}")

    # --- Step 1: Fetch raw data from Monday.com ---
    raw_items = await monday.get_all_items(DEALS_BOARD_ID)
    logger.info(f"Fetched {len(raw_items)} raw deal items from Monday.com")

    # --- Step 2: Normalize every item ---
    normalized = [normalize_deal(item) for item in raw_items]

    # --- Step 3: Remove embedded header rows ---
    normalized = drop_header_rows(normalized)
    logger.info(f"After normalization and header removal: {len(normalized)} deals")

    # --- Step 4: Apply filters ---
    filters = {key: tool_input.get(key) for key in DEAL_FILTER_KEYS}
    filtered = apply_filters(normalized, filters)
    logger.info(f"After filtering: {len(filtered)} deals match criteria")

    # --- Step 5: Route to output format ---
    if output_format == "records":
        # Return individual deal rows for listing queries
        # Cap at 50 to avoid overwhelming context window
        return {
            "count": len(filtered),
            "sector": tool_input.get("sector", "All"),
            "deals": [format_deal_record(d) for d in filtered[:50]],
            "data_quality_notes": extract_deal_caveats(filtered),
        }
    else:
        # DEFAULT: Chain analytics internally
        return compute_pipeline_summary(
            filtered,
            sector=tool_input.get("sector"),
        )


async def _handle_work_orders(
    tool_input: dict[str, Any],
    output_format: str
) -> dict:
    """
    Internal handler for query_work_orders tool calls.

    Same pattern as _handle_deals but for the Work Orders board.

    Args:
        tool_input: Tool parameters
        output_format: "summary" or "records"

    Returns:
        Summary dict or records dict
    """
    logger.info(f"Handling query_work_orders: filters={tool_input}, format={output_format}")

    # --- Step 1: Fetch raw data ---
    raw_items = await monday.get_all_items(WO_BOARD_ID)
    logger.info(f"Fetched {len(raw_items)} raw work order items from Monday.com")

    # --- Step 2: Normalize ---
    normalized = [normalize_work_order(item) for item in raw_items]
    logger.info(f"Normalized {len(normalized)} work orders")

    # --- Step 3: Apply filters ---
    filters = {key: tool_input.get(key) for key in WO_FILTER_KEYS}
    filtered = apply_filters(normalized, filters)
    logger.info(f"After filtering: {len(filtered)} work orders match criteria")

    # --- Step 4: Route to output format ---
    if output_format == "records":
        return {
            "count": len(filtered),
            "sector": tool_input.get("sector", "All"),
            "work_orders": [format_wo_record(w) for w in filtered[:50]],
            "data_quality_notes": extract_wo_caveats(filtered),
        }
    else:
        # DEFAULT: Chain revenue analytics internally
        return compute_revenue_summary(
            filtered,
            sector=tool_input.get("sector"),
        )
