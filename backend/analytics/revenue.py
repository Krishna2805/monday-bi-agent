"""
revenue.py — Work Order Revenue & Operations Analytics
========================================================

WHY THIS FILE EXISTS:
    This module computes all financial and operational metrics from
    the Work Orders board. It answers questions like:
      - "What's our total billed revenue?"
      - "How much AR is outstanding?"
      - "How many projects are ongoing vs completed?"
      - "What's unbilled across all work orders?"

    Like pipeline.py, these functions are:
      - Pure: no API calls, no side effects
      - Deterministic: same input → same output
      - Independently testable

BUSINESS CONTEXT:
    Work orders represent actual contracted work (not prospects).
    Each work order has a lifecycle:
    
    PO Received → Execution → Billing → Collection
    
    Key financial metrics at each stage:
    - PO Value (amount_excl_gst): Total contract value
    - Billed (billed_excl_gst): How much has been invoiced to the client
    - Collected (collected_incl_gst): How much cash has been received
    - Unbilled (amount_to_bill_excl_gst): Work done but not yet invoiced
    - AR Outstanding (amount_receivable): Invoiced but not yet collected

    GST CONVENTION:
    - Revenue figures use EXCL-GST (what the company actually earns)
    - Collection figures use INCL-GST (what the client actually pays)
    - AR uses INCL-GST (what's owed including tax)
    This convention is defined in the project requirements and must
    be consistent throughout the codebase.

OPERATIONAL METRICS:
    Beyond financials, work orders track project execution:
    - Execution Status: Completed, Ongoing, Not Started, Pause/struck
    - Contract Type: One-time, Monthly, Annual, POC
    - Sector: Mining, Renewables, Powerline, Railways, Construction
"""

from normalizer.amount_fix import safe_sum
from analytics.aggregator import group_by_field, extract_wo_caveats


def compute_revenue_summary(
    work_orders: list[dict],
    sector: str | None = None,
    group_by: str | None = None
) -> dict:
    """
    Compute comprehensive revenue and operational metrics from work orders.

    This is the PRIMARY analytics function for the Work Orders board.
    It's called internally by tool_handler.py when query_work_orders
    is invoked with output_format="summary" (the default).

    Args:
        work_orders: List of normalized work order dicts.
        sector: Optional sector filter.
        group_by: Optional grouping dimension (e.g., "sector",
                  "contract_type", "execution_status", "billing_status").

    Returns:
        A summary dict containing all revenue and ops KPIs:
        {
            "sector": "Mining" or "All",
            "work_order_count": 45,

            # --- Financial Metrics ---
            "total_po_value_inr": 50000000,         # Total contract value
            "total_billed_excl_gst_inr": 35000000,  # Invoiced amount
            "total_collected_incl_gst_inr": 28000000,# Cash received
            "total_unbilled_inr": 15000000,          # Work done, not invoiced
            "total_ar_outstanding_inr": 7000000,     # Invoiced, not collected

            # --- Derived Financial Metrics ---
            "billing_percentage": 70.0,              # billed / PO value × 100
            "collection_percentage": 80.0,           # collected / billed × 100

            # --- Operational Metrics ---
            "execution_breakdown": {"Completed": 20, "Ongoing": 15, ...},
            "contract_type_breakdown": {"One time Project": 25, ...},
            "sector_breakdown": {"Mining": 12, ...},

            "data_quality_notes": ["3 POC entries excluded", ...]
        }

    WHAT EACH METRIC MEANS:

        total_po_value_inr:
            Sum of all PO (Purchase Order) amounts, excl GST.
            This is "total contracted revenue" — how much work has
            been formally ordered by clients.

        total_billed_excl_gst_inr:
            Sum of invoiced amounts, excl GST.
            This is "how much we've asked clients to pay".
            Difference from PO value = work ordered but not yet invoiced.

        total_collected_incl_gst_inr:
            Sum of actual payments received, incl GST.
            Uses incl-GST because that's what actually hits the bank.
            This is "cash in hand".

        total_unbilled_inr:
            Sum of (work done but not yet invoiced), excl GST.
            High unbilled amounts indicate a billing bottleneck —
            the company has done the work but hasn't sent invoices.

        total_ar_outstanding_inr:
            Sum of (invoiced but not yet collected), incl GST.
            This is "money clients owe us". High AR indicates
            collection issues or slow-paying clients.

        billing_percentage:
            (Billed / PO Value) × 100.
            Shows what fraction of contracted work has been invoiced.
            A low % means billing is lagging behind execution.

        collection_percentage:
            (Collected / Billed) × 100.
            Shows what fraction of invoiced amounts have been collected.
            A low % indicates payment collection issues.
    """
    # --- Optional sector filter ---
    if sector:
        work_orders = [
            w for w in work_orders
            if str(w.get("sector", "")).lower() == sector.lower()
        ]

    # --- Financial Aggregations ---
    # Each call to safe_sum returns (total, null_count).
    # We track null counts for data quality reporting.

    # PO Value — total contracted amount (excl GST for revenue view)
    total_po, po_nulls = safe_sum(
        [w.get("amount_excl_gst") for w in work_orders]
    )

    # Billed — how much has been invoiced (excl GST)
    total_billed, billed_nulls = safe_sum(
        [w.get("billed_excl_gst") for w in work_orders]
    )

    # Collected — cash received (incl GST, per project requirements)
    total_collected, collected_nulls = safe_sum(
        [w.get("collected_incl_gst") for w in work_orders]
    )

    # Unbilled — work done but not invoiced (excl GST)
    total_unbilled, unbilled_nulls = safe_sum(
        [w.get("amount_to_bill_excl_gst") for w in work_orders]
    )

    # AR Outstanding — invoiced but not collected
    total_ar, ar_nulls = safe_sum(
        [w.get("amount_receivable") for w in work_orders]
    )

    # --- Derived Financial Metrics ---
    # Billing percentage: what fraction of PO value has been billed
    billing_pct = (
        round(total_billed / total_po * 100, 1)
        if total_po > 0
        else None
    )

    # Collection percentage: what fraction of billed has been collected
    # Note: collected is incl-GST, billed is excl-GST. For a proper
    # apples-to-apples comparison, we'd need billed incl-GST. But since
    # we use this as a directional indicator (not exact accounting),
    # this approximation is acceptable for BI purposes.
    collection_pct = (
        round(total_collected / (total_billed * 1.18) * 100, 1)
        if total_billed > 0
        else None
    )

    # --- Operational Breakdowns ---
    # Execution status distribution
    exec_breakdown: dict[str, int] = {}
    for w in work_orders:
        status = w.get("execution_status", "Unknown")
        if not status:
            status = "Unknown"
        exec_breakdown[status] = exec_breakdown.get(status, 0) + 1

    # Contract type distribution
    contract_breakdown: dict[str, int] = {}
    for w in work_orders:
        ctype = w.get("contract_type", "Unknown")
        if not ctype:
            ctype = "Unknown"
        contract_breakdown[ctype] = contract_breakdown.get(ctype, 0) + 1

    # Sector distribution (useful when no sector filter is applied)
    sector_breakdown: dict[str, int] = {}
    for w in work_orders:
        s = w.get("sector", "Unknown")
        if not s:
            s = "Unknown"
        sector_breakdown[s] = sector_breakdown.get(s, 0) + 1

    # --- Data Quality Notes ---
    notes = extract_wo_caveats(work_orders)

    # --- Build Result ---
    result = {
        "sector": sector or "All",
        "work_order_count": len(work_orders),

        # Financial totals (all rounded to avoid floating point noise)
        "total_po_value_inr": round(total_po),
        "total_billed_excl_gst_inr": round(total_billed),
        "total_collected_incl_gst_inr": round(total_collected),
        "total_unbilled_inr": round(total_unbilled),
        "total_ar_outstanding_inr": round(total_ar),

        # Derived percentages
        "billing_percentage": billing_pct,
        "collection_percentage": collection_pct,

        # Operational breakdowns
        "execution_breakdown": exec_breakdown,
        "contract_type_breakdown": contract_breakdown,
        "sector_breakdown": sector_breakdown,

        # Data quality
        "data_quality_notes": notes,
    }

    # --- Optional Grouping ---
    if group_by:
        result["breakdown"] = group_by_field(
            work_orders, group_by, compute_revenue_summary
        )

    return result
