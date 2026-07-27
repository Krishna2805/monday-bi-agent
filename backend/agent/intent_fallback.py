"""
intent_fallback.py — Keyword-Based Intent Classifier
======================================================

WHY THIS FILE EXISTS:
    LLM tool selection is reliable, but under high concurrency or for vague
    queries, intent classification provides a deterministic fallback:
      1. Detects domain intent (pipeline, revenue, operations) instantly
      2. Ensures the appropriate tool handler is executed deterministically

HOW IT FITS IN THE FLOW:
    1. User asks a question
    2. classify_intent() runs on raw question text (instant, zero API overhead)
    3. Returns target intent category ("pipeline", "revenue", "operations")
    4. Routes to the primary tool handler in INTENT_TOOL_MAP

    The fallback acts as a DETERMINISTIC SAFETY NET for routing.

THREE INTENT CATEGORIES:

    1. "pipeline" — Questions about sales deals, funnel, conversions
       Maps to: query_deals
       Examples: "How is the pipeline?", "Show won deals", "What's our win rate?"

    2. "revenue" — Questions about financial metrics
       Maps to: query_work_orders
       Examples: "What's our AR?", "How much have we collected?", "Billing status"

    3. "operations" — Questions about project execution and delivery
       Maps to: query_work_orders (same board, different intent)
       Examples: "Which projects are delayed?", "What's ongoing?", "Project status"

    WHY OPERATIONS IS SEPARATE FROM REVENUE:
       Work orders contain BOTH financial data (billing, AR) AND
       operational data (execution status, delays). A query like
       "Which projects are delayed?" has nothing to do with revenue
       keywords like "billing" or "AR". Without the operations
       category, this query would get no intent match, and if the LLM
       also misses, the user gets no data.

KEYWORD SCORING:
    We count how many keywords from each category appear in the query.
    The category with the highest count wins. This is simple but
    effective because:
    - Business queries are usually domain-specific ("pipeline",
      "AR outstanding", "delayed projects" are unambiguous)
    - Ties are rare (a question about both pipeline AND revenue
      is unusual in practice)
    - If no keywords match at all, we return None and let the LLM
      handle it (the query might be a greeting or clarification)
"""

import logging

logger = logging.getLogger(__name__)

# ============================================================
# KEYWORD SETS
# ============================================================
# Each set contains words/phrases that strongly indicate a
# particular intent. The words are all lowercase — we lowercase
# the query before matching.
#
# IMPORTANT: "work order" was moved from REVENUE to OPERATIONS
# because "work order" is an operational concept (project tracking),
# not purely financial. Revenue keywords focus on money flow.

PIPELINE_KEYWORDS = {
    "pipeline",
    "deal",
    "deals",
    "sales",
    "funnel",
    "won",
    "open deal",
    "lead",
    "prospect",
    "negotiation",
    "closure",
    "conversion",
    "win rate",
    "probability",
    "deal stage",
    "dead deal",
}

REVENUE_KEYWORDS = {
    "revenue",
    "billing",
    "billed",
    "collection",
    "collected",
    "ar",
    "accounts receivable",
    "unbilled",
    "invoice",
    "payment",
    "po value",
    "outstanding",
    "receivable",
    "financial",
}

OPERATIONS_KEYWORDS = {
    "project",
    "execution",
    "delayed",
    "delay",
    "ongoing",
    "completed",
    "status",
    "work order",
    "workorder",
    "not started",
    "paused",
    "struck",
    "delivery",
    "operational",
}


def classify_intent(query: str) -> str | None:
    """
    Classify a user query into a business intent category.

    This is a fast, deterministic classifier that runs BEFORE the
    LLM generation call. It provides a fallback intent for tool routing.

    Args:
        query: The raw user question text (e.g., "How is our pipeline?")

    Returns:
        "pipeline", "revenue", "operations", or None.
        None means no clear intent was detected.

    HOW SCORING WORKS:
        For each keyword set, count how many keywords appear in the query.
        The set with the highest count wins. If all counts are 0, return None.

    Examples:
        "How is the Mining pipeline?" → "pipeline" (matches "pipeline")
        "What's our AR outstanding?" → "revenue" (matches "ar", "outstanding")
        "Which projects are delayed?" → "operations" (matches "project", "delayed")
        "Hello, how are you?" → None (no keywords match)
    """
    q = query.lower()

    scores = {
        "pipeline": sum(1 for kw in PIPELINE_KEYWORDS if kw in q),
        "revenue": sum(1 for kw in REVENUE_KEYWORDS if kw in q),
        "operations": sum(1 for kw in OPERATIONS_KEYWORDS if kw in q),
    }

    best_intent = max(scores, key=scores.get)

    if scores[best_intent] > 0:
        logger.debug(
            f"Intent classified as '{best_intent}' "
            f"(scores: {scores}) for query: '{query[:50]}...'"
        )
        return best_intent

    logger.debug(f"No intent detected for query: '{query[:50]}...'")
    return None


# ============================================================
# INTENT → TOOL MAPPING
# ============================================================
# Maps each intent category to the tool(s) that should be called.
# Since we only have 2 tools, this is straightforward:
#   - pipeline questions → query_deals
#   - revenue questions → query_work_orders
#   - operations questions → query_work_orders (same board)
#
# The list format supports future expansion (e.g., if we add a
# cross-board analysis tool), but currently each intent maps to
# exactly one tool.
INTENT_TOOL_MAP = {
    "pipeline": ["query_deals"],
    "revenue": ["query_work_orders"],
    "operations": ["query_work_orders"],
}
