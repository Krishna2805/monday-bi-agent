"""
pipeline.py — Deal Pipeline Analytics
=======================================

WHY THIS FILE EXISTS:
    This module computes all deal pipeline metrics. It takes a list
    of normalized deal dicts (from normalize_deal()) and returns a
    summary JSON dict that Gemini uses to explain pipeline health.

    These functions are:
      - Pure: no API calls, no side effects, no Gemini interaction
      - Deterministic: same input always produces same output
      - Independently testable: pass in sample data, check the output

BUSINESS CONTEXT:
    The company is a drone survey / geospatial services provider.
    Their deal pipeline tracks prospects from lead generation through
    to won/dead. Key metrics the leadership wants:

    1. Pipeline Value: Total value of all open deals (potential revenue)
    2. Weighted Pipeline: Pipeline adjusted by probability of closing
       - High probability (80%): deal is very likely to close
       - Medium (50%): could go either way
       - Low (20%): long shot but still being pursued
    3. Win Rate: what % of resolved deals were won (not open/on-hold)
    4. Stage Funnel: how many deals are at each stage of the process
    5. Sector Breakdown: pipeline split by industry vertical

PROBABILITY WEIGHTS EXPLANATION:
    These weights convert qualitative probability labels into numbers
    for calculating "risk-adjusted pipeline value":
    
    Example:
        10 open deals × ₹10L each = ₹1Cr total pipeline
        But if 5 are "Low" probability:
        Weighted = (5 × 10L × 0.8) + (3 × 10L × 0.5) + (2 × 10L × 0.2)
                 = 40L + 15L + 4L = ₹59L weighted pipeline
    
    The weighted value is more realistic because it discounts deals
    that are unlikely to close. Leadership uses this for cash flow
    forecasting.
"""

from normalizer.amount_fix import safe_sum
from analytics.aggregator import group_by_field, extract_deal_caveats

# ============================================================
# PROBABILITY WEIGHTS
# ============================================================
# These map the qualitative probability labels from Monday.com
# to numeric weights. The values were defined in the project
# requirements (not invented by us).
#
# High = 80% chance of closing
# Medium = 50% chance
# Low = 20% chance
# Empty/Unknown = 0% (excluded from weighted calculation)
PROBABILITY_WEIGHTS = {
    "High": 0.8,
    "Medium": 0.5,
    "Low": 0.2,
}


def compute_pipeline_summary(
    deals: list[dict],
    sector: str | None = None,
    group_by: str | None = None
) -> dict:
    """
    Compute comprehensive pipeline metrics from normalized deals.

    This is the PRIMARY analytics function for the Deals board.
    It's called internally by tool_handler.py when Gemini invokes
    query_deals with output_format="summary" (the default).

    Args:
        deals: List of normalized deal dicts (from normalize_deal()).
               These should already have header rows removed.
        sector: Optional sector filter (e.g., "Mining"). If provided,
                only deals in that sector are included.
        group_by: Optional grouping dimension (e.g., "sector", "stage",
                  "probability"). If provided, returns a breakdown dict.

    Returns:
        A summary dict containing all pipeline KPIs:
        {
            "sector": "Mining" or "All",
            "total_deals": 45,
            "open_deals": 24,
            "won_deals": 15,
            "dead_deals": 6,
            "total_pipeline_inr": 45000000,      # sum of open deal values
            "weighted_pipeline_inr": 18000000,    # probability-adjusted
            "win_rate_pct": 71.4,                 # won / (won + dead) * 100
            "high_probability_count": 9,
            "stage_breakdown": {"Negotiations": 8, "Proposal Sent": 10, ...},
            "probability_breakdown": {"High": 9, "Medium": 10, "Low": 5},
            "data_quality_notes": ["5 deals missing values", ...]
        }

    WHY SO MANY METRICS IN ONE FUNCTION:
        Because the tool_handler calls this once and gives everything
        to Gemini. If we split into separate functions (get_win_rate,
        get_pipeline_value, etc.), each would need to filter and iterate
        the same data independently — wasteful. One pass, all metrics.

    WHAT EACH METRIC MEANS:

        total_pipeline_inr:
            Sum of deal_value for all open deals. This is the "maximum
            possible revenue if every deal closes". Useful but optimistic.

        weighted_pipeline_inr:
            Sum of (deal_value × probability_weight) for open deals.
            This is the "expected revenue adjusted for likelihood".
            More realistic for forecasting.

        win_rate_pct:
            Won deals / (Won + Dead deals) × 100.
            We exclude "Open" and "On Hold" deals because they haven't
            been resolved yet. Including them would make the win rate
            artificially low.
            Returns None if no deals have been resolved (avoid div by zero).

        stage_breakdown:
            Counts of open deals at each stage. Shows the "shape" of
            the funnel. A healthy funnel is wide at the top (many leads)
            and narrower at the bottom (fewer in negotiations).

        high_probability_count:
            How many open deals are rated "High" probability.
            These are the most likely to close and contribute to
            near-term revenue.
    """
    # --- Optional sector filter ---
    if sector:
        deals = [
            d for d in deals
            if str(d.get("sector", "")).lower() == sector.lower()
        ]

    # --- Categorize by status ---
    open_deals = [d for d in deals if d.get("deal_status") == "Open"]
    won_deals = [d for d in deals if d.get("deal_status") == "Won"]
    dead_deals = [d for d in deals if d.get("deal_status") == "Dead"]
    on_hold_deals = [d for d in deals if d.get("deal_status") == "On Hold"]

    # --- Total Pipeline Value (open deals only) ---
    # We only count open deals because won deals are already revenue
    # and dead deals are gone. The pipeline is "what might still close".
    pipeline_values = [d.get("deal_value") for d in open_deals]
    total_pipeline, null_count = safe_sum(pipeline_values)

    # --- Weighted Pipeline Value ---
    # For each open deal: value × probability_weight
    # If deal_value is None, we skip it (contributes 0)
    # If probability is empty/unknown, weight is 0 (conservative)
    weighted = 0.0
    for d in open_deals:
        value = d.get("deal_value")
        if value is None:
            continue
        prob = d.get("probability", "")
        weight = PROBABILITY_WEIGHTS.get(prob, 0)
        weighted += value * weight

    # --- Win Rate ---
    # Only count resolved deals (Won + Dead). Open deals are unresolved.
    # This prevents the win rate from dropping just because we have
    # many new leads that haven't been worked yet.
    total_resolved = len(won_deals) + len(dead_deals)
    win_rate = (
        round(len(won_deals) / total_resolved * 100, 1)
        if total_resolved > 0
        else None  # Not enough data to calculate
    )

    # --- Stage Funnel Breakdown (open deals only) ---
    # Counts how many open deals are at each stage.
    # Useful for identifying bottlenecks (e.g., too many stuck in "Proposal Sent")
    stage_breakdown: dict[str, int] = {}
    for d in open_deals:
        stage = d.get("deal_stage", "Unknown")
        if not stage:
            stage = "Unknown"
        stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

    # --- Probability Breakdown (open deals only) ---
    # Counts by probability level — shows confidence distribution
    prob_breakdown: dict[str, int] = {}
    for d in open_deals:
        prob = d.get("probability", "Unknown")
        if not prob:
            prob = "Unknown"
        prob_breakdown[prob] = prob_breakdown.get(prob, 0) + 1

    # --- High Probability Count ---
    high_prob_count = sum(
        1 for d in open_deals if d.get("probability") == "High"
    )

    # --- Data Quality Notes ---
    notes = extract_deal_caveats(deals)

    # --- Build result ---
    result = {
        "sector": sector or "All",
        "total_deals": len(deals),
        "open_deals": len(open_deals),
        "won_deals": len(won_deals),
        "dead_deals": len(dead_deals),
        "on_hold_deals": len(on_hold_deals),
        "total_pipeline_inr": round(total_pipeline),
        "weighted_pipeline_inr": round(weighted),
        "win_rate_pct": win_rate,
        "high_probability_count": high_prob_count,
        "stage_breakdown": stage_breakdown,
        "probability_breakdown": prob_breakdown,
        "data_quality_notes": notes,
    }

    # --- Optional Grouping ---
    # If group_by is specified, add a breakdown dict
    # e.g., group_by="sector" adds result["breakdown"]["Mining"] = {...}
    if group_by:
        result["breakdown"] = group_by_field(
            deals, group_by, compute_pipeline_summary
        )

    return result
