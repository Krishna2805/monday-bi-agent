"""
queries.py — Monday.com GraphQL Query Strings
==============================================

WHY THIS FILE EXISTS:
    All GraphQL queries are centralized here so that:
      1. Query strings are easy to review, test, and modify in one place
      2. No GraphQL is scattered across business logic files
      3. If Monday.com's API version changes, we update queries here only

HOW MONDAY.COM'S API WORKS:
    Monday.com uses GraphQL (not REST). Every request is a POST to
    https://api.monday.com/v2 with a JSON body containing a "query" string.
    
    Key concepts:
    - A "board" is a table (like a spreadsheet)
    - An "item" is a row in that table
    - "column_values" are the cells in that row
    - Each column has an internal ID (e.g., "text0", "status4") that
      differs from the display name. We map these in column_maps.py
    
    Pagination:
    - Monday.com returns max 100 items per request
    - It uses cursor-based pagination: each response includes a "cursor"
      string. Pass it back in the next request to get the next page.
    - When cursor is null, you've reached the last page.

QUERY PARAMETERS:
    $board_id (ID!): The numeric ID of the Monday.com board
    $cursor (String): Pagination cursor, null for the first page
"""

# ============================================================
# GET_BOARD_ITEMS — Fetch all items (rows) from a board
# ============================================================
# This is the primary data retrieval query. It fetches items in
# pages of 100, returning each item's:
#   - id: Monday.com's internal item ID
#   - name: The item name (first column / row title)
#   - column_values: All cell values for that row
#       - id: Column ID (e.g., "text0") — mapped in column_maps.py
#       - text: Human-readable text representation of the value
#       - value: Raw JSON string with the full column value
#
# We request both `text` and `value` because:
#   - `text` is what the user sees in Monday.com (e.g., "Mining")
#   - `value` contains structured data (e.g., status index, date
#     objects) that we may need for precise parsing
#
# The `items_page` approach with cursor is Monday.com's recommended
# pagination method (replaces the older `items(limit, page)` which
# is deprecated in API version 2024-01+).
GET_BOARD_ITEMS = """
query GetBoardItems($board_id: ID!, $cursor: String) {
  boards(ids: [$board_id]) {
    items_page(limit: 100, cursor: $cursor) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          value
        }
      }
    }
  }
}
"""

# ============================================================
# GET_BOARD_COLUMNS — Discover column IDs and types for a board
# ============================================================
# This query is used ONCE during initial setup to discover the
# mapping between Monday.com's internal column IDs and their
# human-readable titles.
#
# Example response:
#   {"id": "text0", "title": "Customer Name Code", "type": "text"}
#   {"id": "status4", "title": "Execution Status", "type": "status"}
#
# After running this, you fill in column_maps.py with the actual
# ID → semantic name mappings for your specific boards.
#
# WHY NOT AUTO-DISCOVER AT RUNTIME?
#   We could, but it adds an API call on every request and makes
#   the mapping implicit. Explicit maps in column_maps.py are:
#   - Debuggable: you can read the file and see the mapping
#   - Testable: unit tests use the same map
#   - Stable: column renames in Monday.com don't silently break things
GET_BOARD_COLUMNS = """
query GetColumns($board_id: ID!) {
  boards(ids: [$board_id]) {
    columns {
      id
      title
      type
    }
  }
}
"""
