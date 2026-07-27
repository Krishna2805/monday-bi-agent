"""
column_maps.py — Monday.com Column ID → Semantic Name Mappings
===============================================================

WHY THIS FILE EXISTS:
    Monday.com identifies each column by an internal ID like "color_mm5ne3dn",
    "numeric_mm5nkavy", etc. These IDs are board-specific and not human-readable.

    This file maps those internal IDs to meaningful Python-friendly names
    so the rest of our code can work with "sector" instead of "color_mm5ncftm".

STATUS:
    FULLY POPULATED with actual column IDs fetched directly from Monday.com API.
"""

# ============================================================
# DEALS BOARD — Deal Funnel / Pipeline
# ============================================================
DEALS_COLUMN_MAP = {
    "color_mm5ne3dn":         "owner_code",          # Owner code
    "dropdown_mm5na1k5":      "client_code",         # Client Code
    "color_mm5nwmpp":         "deal_status",         # Deal Status (Open, Won, Dead, On Hold)
    "date_mm5n5rfh":          "close_date_actual",   # Close Date (A)
    "color_mm5n67xa":         "probability",         # Closure Probability (High, Medium, Low)
    "numeric_mm5nkavy":       "deal_value",          # Masked Deal value
    "date_mm5n9x82":          "tentative_close_date",# Tentative Close Date
    "color_mm5ncsmb":         "deal_stage",          # Deal Stage (A. Lead Generated → N. Not relevant)
    "color_mm5n4v0h":         "product_deal",        # Product deal
    "color_mm5ncftm":         "sector",              # Sector/service (Mining, Renewables, etc.)
    "date_mm5nab0a":          "created_date",        # Created Date
}

# ============================================================
# WORK ORDERS BOARD — Work Order Tracker
# ============================================================
WORK_ORDER_COLUMN_MAP = {
    # --- Identity & Classification ---
    "text_mm5nz5zx":          "customer_name_code",  # Customer Name Code
    "text_mm5n5r5z":          "serial_number",       # Serial #
    "dropdown_mm5nmbw1":      "contract_type",       # Nature of Work (One time Project, Monthly Contract, etc.)
    "color_mm5nawf8":         "last_executed_month", # Last executed month of recurring project

    # --- Execution ---
    "color_mm5nc8ar":         "execution_status",    # Execution Status (Completed, Ongoing, etc.)
    "date_mm5n1cnw":          "data_delivery_date",  # Data Delivery Date
    "date_mm5nardp":          "po_date",             # Date of PO/LOI
    "dropdown_mm5nxys3":      "document_type",       # Document Type
    "date_mm5nd6xn":          "probable_start_date", # Probable Start Date
    "date_mm5nmchz":          "probable_end_date",   # Probable End Date

    # --- Personnel & Classification ---
    "text_mm5ng4tk":          "bd_personnel_code",   # BD/KAM Personnel code
    "dropdown_mm5nwqzm":      "sector",              # Sector
    "dropdown_mm5n4m2b":      "work_type",           # Type of Work
    "color_mm5nvbme":         "software_platform",   # Is any Skylark software platform part of deliverables

    # --- Financial (all amounts in INR, "Masked" label is anonymization marker) ---
    "date_mm5nawh5":          "last_invoice_date",   # Last invoice date
    "dropdown_mm5ntfdh":      "latest_invoice_no",   # latest invoice no.
    "numeric_mm5n3k9g":       "amount_excl_gst",     # Amount in Rupees (Excl of GST) (Masked)
    "numeric_mm5n29da":       "amount_incl_gst",     # Amount in Rupees (Incl of GST) (Masked)
    "numeric_mm5nxndw":       "billed_excl_gst",     # Billed Value in Rupees (Excl of GST.) (Masked)
    "numeric_mm5n2q1c":       "billed_incl_gst",     # Billed Value in Rupees (Incl of GST.) (Masked)
    "numeric_mm5nc08n":       "collected_incl_gst",  # Collected Amount in Rupees (Incl of GST.) (Masked)
    "numeric_mm5ne53s":       "amount_to_bill_excl_gst", # Amount to be billed in Rs. (Exl. of GST) (Masked)
    "numeric_mm5n39rj":       "amount_to_bill_incl_gst", # Amount to be billed in Rs. (Incl. of GST) (Masked)
    "numeric_mm5nbgcy":       "amount_receivable",   # Amount Receivable (Masked)

    # --- AR & Billing Status ---
    "color_mm5n4rn4":         "ar_priority",         # AR Priority account
    "numeric_mm5nc763":       "quantity_by_ops",     # Quantity by Ops
    "dropdown_mm5n8rec":      "quantity_as_per_po",  # Quantities as per PO
    "numeric_mm5n4xc8":       "quantity_billed",     # Quantity billed (till date)
    "numeric_mm5nr18k":       "balance_quantity",    # Balance in quantity

    # --- Status Tracking ---
    "color_mm5ny5jm":         "invoice_status",      # Invoice Status
    "text_mm5n28q8":          "expected_billing_month",  # Expected Billing Month
    "color_mm5n5xyg":         "actual_billing_month",    # Actual Billing Month
    "text_mm5nq1b3":          "actual_collection_month", # Actual Collection Month
    "color_mm5nb6be":         "wo_status_billed",    # WO Status (billed)
    "text_mm5ncad8":          "collection_status",   # Collection status
    "text_mm5n5qw2":          "collection_date",     # Collection Date
    "color_mm5nxkfn":         "billing_status",      # Billing Status
}


if __name__ == "__main__":
    import asyncio
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from config import WO_BOARD_ID, DEALS_BOARD_ID
    from monday.client import MondayClient

    async def discover():
        client = MondayClient()

        print("=" * 60)
        print("DEALS BOARD COLUMNS")
        print("=" * 60)
        deals_cols = await client.get_board_columns(DEALS_BOARD_ID)
        for col in deals_cols:
            print(f"  ID: {col['id']:20s}  Title: {col['title']:45s}  Type: {col['type']}")

        print()
        print("=" * 60)
        print("WORK ORDERS BOARD COLUMNS")
        print("=" * 60)
        wo_cols = await client.get_board_columns(WO_BOARD_ID)
        for col in wo_cols:
            print(f"  ID: {col['id']:20s}  Title: {col['title']:45s}  Type: {col['type']}")

        print()
        print("Copy the IDs above into the maps in this file.")

    asyncio.run(discover())
