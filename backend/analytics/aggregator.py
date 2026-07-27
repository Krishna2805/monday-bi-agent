"""
aggregator.py — Shared Filtering and Grouping Utilities
=========================================================

WHY THIS FILE EXISTS:
    Both pipeline.py and revenue.py need to filter data by sector,
    status, etc., and group data by various dimensions. Rather than
    duplicating this logic, we centralize it here.

    This module contains ONLY generic utilities — no business-specific
    calculations. It answers "which items match?" and "how do items
    group?", not "what is the win rate?".

DESIGN PRINCIPLES:
    1. All functions are pure (no side effects, no API calls)
    2. All functions take lists of dicts and return lists/dicts of dicts
    3. Filters are composable — you can chain multiple filters
    4. Grouping is generic — works with any field name
"""

from typing import Any, Callable, Optional


def filter_by_field(
    items: list[dict],
    field: str,
    value: str,
    case_insensitive: bool = True
) -> list[dict]:
    """
    Filter a list of dicts by exact match on a single field.

    Args:
        items: List of normalized dicts (deals or work orders)
        field: The field name to filter on (e.g., "sector", "deal_status")
        value: The value to match (e.g., "Mining", "Open")
        case_insensitive: If True, comparison ignores case (default: True)

    Returns:
        A new list containing only items where item[field] matches value.

    WHY CASE-INSENSITIVE BY DEFAULT:
        Users might type "mining" or "Mining" or "MINING" in their query.
        The tool input normalizes this somewhat, but the filter should be lenient.
        Monday.com's display values are also inconsistent in casing.

    Examples:
        filter_by_field(deals, "sector", "Mining")
        filter_by_field(work_orders, "execution_status", "Completed")
    """
    if case_insensitive:
        target = value.lower()
        return [
            item for item in items
            if str(item.get(field, "")).lower() == target
        ]
    else:
        return [
            item for item in items
            if item.get(field) == value
        ]


def apply_filters(items: list[dict], filters: dict[str, Optional[str]]) -> list[dict]:
    """
    Apply multiple field filters to a list of items.

    This is the main filtering function used by tool_handler.py.
    It takes the filter parameters from the tool call and
    applies them sequentially.

    Args:
        items: List of normalized dicts
        filters: Dict of {field_name: filter_value}.
                 None values are skipped (meaning "no filter on this field").

    Returns:
        Filtered list of items matching ALL non-None filters.

    HOW IT WORKS:
        Filters are applied sequentially (AND logic). Each filter
        reduces the list further. Order doesn't matter for correctness
        but we apply them in dict order.

    Example:
        # Tool call query_deals(sector="Mining", deal_status="Open")
        # tool_handler converts this to:
        filters = {"sector": "Mining", "deal_status": "Open", "probability": None}
        result = apply_filters(deals, filters)
        # Returns only Mining + Open deals (probability not filtered)
    """
    result = items
    for field, value in filters.items():
        if value is not None:
            result = filter_by_field(result, field, value)
    return result


def group_by_field(
    items: list[dict],
    field: str,
    compute_fn: Callable[[list[dict]], Any]
) -> dict[str, Any]:
    """
    Group items by a field and apply a computation to each group.

    This powers "breakdown by sector" and similar grouped analytics.
    It splits items into groups based on a field value, then runs
    the provided computation function on each group.

    Args:
        items: List of normalized dicts
        field: The field to group by (e.g., "sector", "deal_stage")
        compute_fn: A function that takes (items, sector=None) and
                    returns a summary dict. This is typically
                    compute_pipeline_summary or compute_revenue_summary.

    Returns:
        A dict where keys are field values and values are computed summaries.
        Example:
        {
            "Mining": {"open_deals": 5, "pipeline_value": 1000000, ...},
            "Renewables": {"open_deals": 3, "pipeline_value": 500000, ...}
        }

    WHY PASS compute_fn INSTEAD OF IMPORTING IT:
        Passing the function avoids circular imports. pipeline.py and
        revenue.py both use this module, and this module uses their
        compute functions. By passing the function as an argument,
        we break the circular dependency.
    """
    # Build groups: {field_value: [items]}
    groups: dict[str, list[dict]] = {}
    for item in items:
        key = str(item.get(field, "Unknown")).strip()
        if not key:
            key = "Unknown"
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    # Compute summary for each group
    result = {}
    for key, group_items in sorted(groups.items()):
        result[key] = compute_fn(group_items)

    return result


def extract_deal_caveats(deals: list[dict]) -> list[str]:
    """
    Generate data quality caveats for a set of deals.

    These caveats are included in the response JSON so the LLM agent can
    communicate data limitations to the user. This ensures the user
    knows when numbers might be incomplete.

    Args:
        deals: List of normalized deal dicts

    Returns:
        List of human-readable caveat strings.

    Examples:
        ["5 deals have missing deal values — excluded from pipeline total",
         "3 deals have no close date set"]
    """
    notes = []

    # Count deals with missing values
    missing_value = sum(1 for d in deals if d.get("deal_value") is None)
    if missing_value > 0:
        notes.append(
            f"{missing_value} deal(s) have missing deal values — "
            f"excluded from pipeline total"
        )

    # Count deals with missing close dates
    missing_close = sum(
        1 for d in deals
        if d.get("deal_status") == "Open" and not d.get("tentative_close_date")
    )
    if missing_close > 0:
        notes.append(f"{missing_close} open deal(s) have no close date set")

    # Count deals with unknown status
    unknown_status = sum(1 for d in deals if d.get("deal_status") == "Unknown")
    if unknown_status > 0:
        notes.append(f"{unknown_status} deal(s) have unknown status")

    return notes


def extract_wo_caveats(work_orders: list[dict]) -> list[str]:
    """
    Generate data quality caveats for a set of work orders.

    Similar to extract_deal_caveats but for Work Order specific issues.

    Args:
        work_orders: List of normalized work order dicts

    Returns:
        List of human-readable caveat strings.
    """
    notes = []

    # Count WOs with placeholder amounts
    placeholder_count = sum(
        1 for w in work_orders if w.get("_had_placeholder_amount")
    )
    if placeholder_count > 0:
        notes.append(
            f"{placeholder_count} POC/Not Billable entries excluded from financial sums"
        )

    # Count WOs with missing billed amounts
    missing_billed = sum(
        1 for w in work_orders if w.get("billed_excl_gst") is None
    )
    if missing_billed > 0:
        notes.append(f"{missing_billed} work order(s) have missing billed amounts")

    # Count WOs with missing PO amounts
    missing_po = sum(
        1 for w in work_orders if w.get("amount_excl_gst") is None
    )
    if missing_po > 0:
        notes.append(f"{missing_po} work order(s) have missing PO amounts")

    return notes
