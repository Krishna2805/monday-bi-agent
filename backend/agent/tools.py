"""
tools.py — Google GenAI Function Calling Tool Schemas
======================================================

WHY THIS FILE EXISTS:
    Using the official google-genai SDK, function declarations tell
    Gemini what tools exist and what parameters each accepts.

    We expose ONLY 2 retrieval tools:
      - query_deals
      - query_work_orders

    Python handles analytics chaining internally based on output_format:
      - "summary" (default): Returns pre-calculated aggregated KPIs
      - "records": Returns clean individual deal/WO rows
"""

from google.genai import types

query_deals_func = types.FunctionDeclaration(
    name="query_deals",
    description=(
        "Fetch deals pipeline data from Monday.com. "
        "Use for ANY question about: sales pipeline, open/won/dead deals, "
        "deal stages, win rate, pipeline value, weighted pipeline, "
        "deal probability, sector-wise deal analysis, or listing specific deals. "
        "Returns either aggregated pipeline KPIs or individual deal records."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "sector": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Filter by sector: Mining, Renewables, Powerline, "
                    "Railways, Construction, DSP, Tender, Manufacturing. "
                    "Omit for all sectors."
                )
            ),
            "deal_status": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Filter by deal status: Open, Won, Dead, On Hold. "
                    "Omit for all statuses."
                )
            ),
            "probability": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Filter by closure probability: High, Medium, Low. "
                    "Omit for all probability levels."
                )
            ),
            "output_format": types.Schema(
                type=types.Type.STRING,
                description=(
                    "'summary' for aggregated pipeline KPIs like total "
                    "pipeline value, weighted pipeline, win rate, and "
                    "stage breakdown (default). "
                    "'records' for a list of individual deal records "
                    "matching the filters."
                )
            ),
        }
    )
)

query_work_orders_func = types.FunctionDeclaration(
    name="query_work_orders",
    description=(
        "Fetch work order data from Monday.com. "
        "Use for ANY question about: revenue, billing, collections, "
        "accounts receivable (AR), unbilled amounts, project execution "
        "status, delayed projects, ongoing/completed work, operational "
        "health, or listing specific work orders."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "sector": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Filter by sector: Mining, Renewables, Powerline, "
                    "Railways, Construction, Others. Omit for all."
                )
            ),
            "execution_status": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Filter by execution status: Completed, Ongoing, "
                    "Not Started, Executed until current month, "
                    "Pause/struck. Omit for all."
                )
            ),
            "contract_type": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Filter by contract type: One time Project, "
                    "Monthly Contract, Annual Rate Contract, "
                    "Proof of Concept. Omit for all."
                )
            ),
            "output_format": types.Schema(
                type=types.Type.STRING,
                description=(
                    "'summary' for aggregated revenue and operational "
                    "KPIs like total billed, collected, AR outstanding, "
                    "and execution breakdown (default). "
                    "'records' for a list of individual work order "
                    "records matching the filters."
                )
            ),
        }
    )
)

TOOL_SCHEMAS = types.Tool(function_declarations=[query_deals_func, query_work_orders_func])
