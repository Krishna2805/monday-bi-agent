"""
client.py — Async Monday.com GraphQL Client
=============================================

WHY THIS FILE EXISTS:
    This is the ONLY file that talks to Monday.com's API. Every other
    module gets its data through this client. This gives us:
      1. A single place to handle auth headers, timeouts, and retries
      2. Pagination logic hidden from callers — they just get all items
      3. Error handling centralized (API errors, rate limits, timeouts)

DESIGN DECISIONS:

    1. httpx over requests:
       We use httpx because it supports async I/O natively. Since our
       FastAPI server is async, we need non-blocking HTTP calls so one
       slow Monday.com response doesn't freeze all other requests.

    2. Pagination via cursor:
       Monday.com's items_page returns max 100 items per request. We
       loop until cursor is None, collecting all items. For our boards
       (~100-200 rows), this means 1-2 API calls per query.

    3. API-Version header:
       Monday.com requires an API version header. We pin "2024-10" to
       avoid breaking changes from newer API versions.

    4. Retry logic:
       Monday.com rate-limits at 60 requests/minute on free tier.
       We retry on 429 (Too Many Requests) with exponential backoff.
       Other errors (500, network) get one retry with 5s delay.

    5. Error response handling:
       Monday.com sometimes returns 200 OK but with an "errors" key
       in the JSON body. We check for this and raise an exception.
"""

import asyncio
import logging
from typing import Any

import httpx
from cachetools import TTLCache

from config import MONDAY_API_TOKEN
from monday.queries import GET_BOARD_ITEMS, GET_BOARD_COLUMNS

# Global 10-minute TTL cache for board data (max 20 boards)
# Protects against Monday.com 60 req/min rate limit during heavy chat sessions
_board_cache = TTLCache(maxsize=20, ttl=600)

logger = logging.getLogger(__name__)

# Monday.com's single GraphQL endpoint — all queries go here.
MONDAY_API_URL = "https://api.monday.com/v2"

# Maximum number of retries for transient failures (rate limits, server errors).
MAX_RETRIES = 3

# Seconds to wait on first retry. Doubles on each subsequent retry.
BASE_RETRY_DELAY = 2.0


class MondayClient:
    """
    Async client for Monday.com's GraphQL API.

    Usage:
        client = MondayClient()
        items = await client.get_all_items("1234567890")
        columns = await client.get_board_columns("1234567890")

    All methods are async because Monday.com API calls are I/O-bound.
    Using async means FastAPI can serve other requests while we wait
    for Monday.com to respond.
    """

    def __init__(self):
        """
        Initialize with auth headers.

        The Authorization header uses the API token directly (not "Bearer").
        Monday.com's API expects the raw token string.
        Content-Type is application/json for all GraphQL requests.
        API-Version pins us to a specific API version for stability.
        """
        self.headers = {
            "Authorization": MONDAY_API_TOKEN,
            "Content-Type": "application/json",
            "API-Version": "2024-10"
        }

    async def query(self, gql: str, variables: dict[str, Any] | None = None) -> dict:
        """
        Execute a GraphQL query against Monday.com's API.

        Args:
            gql: The GraphQL query string (from queries.py)
            variables: Query variables (e.g., {"board_id": "123"})

        Returns:
            The "data" portion of the API response.

        Raises:
            ValueError: If the API returns errors in the response body.
            httpx.HTTPStatusError: If the HTTP status code indicates failure.

        WHY RETRY LOGIC:
            Monday.com's free tier has strict rate limits (60 req/min).
            During high-traffic demos, we might hit 429 responses.
            Rather than failing immediately, we wait and retry.
            Exponential backoff prevents hammering the API.
        """
        if variables is None:
            variables = {}

        for attempt in range(MAX_RETRIES):
            try:
                # We create a new AsyncClient per request rather than keeping
                # a persistent connection. This is simpler and avoids connection
                # lifecycle issues. For ~100 items across 1-2 pages, the
                # overhead of connection setup is negligible.
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        MONDAY_API_URL,
                        json={"query": gql, "variables": variables},
                        headers=self.headers,
                        timeout=30.0  # 30s timeout — generous for Monday.com
                    )

                    # Handle HTTP-level errors (429, 500, etc.)
                    if response.status_code == 429:
                        # Rate limited — wait and retry
                        delay = BASE_RETRY_DELAY * (2 ** attempt)
                        logger.warning(
                            f"Monday.com rate limit hit (429). "
                            f"Retry {attempt + 1}/{MAX_RETRIES} in {delay}s"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Raise exception for any other non-2xx status
                    response.raise_for_status()

                    data = response.json()

                    # Monday.com can return 200 OK with errors in the body.
                    # Example: {"errors": [{"message": "invalid board ID"}]}
                    # We treat these as hard failures — no retry.
                    if "errors" in data:
                        error_messages = [e.get("message", str(e)) for e in data["errors"]]
                        raise ValueError(
                            f"Monday.com API returned errors: {error_messages}"
                        )

                    return data["data"]

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    # Server error — retry with backoff
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Monday.com server error ({e.response.status_code}). "
                        f"Retry {attempt + 1}/{MAX_RETRIES} in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise  # Non-retryable HTTP error

            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1:
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Monday.com request timed out. "
                        f"Retry {attempt + 1}/{MAX_RETRIES} in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        # Should not reach here, but just in case
        raise RuntimeError(f"Monday.com API failed after {MAX_RETRIES} retries")

    async def get_all_items(self, board_id: str, use_cache: bool = True) -> list[dict]:
        """
        Fetch ALL items from a board, handling pagination and caching automatically.

        Args:
            board_id: The Monday.com board ID (numeric string)
            use_cache: If True (default), returns cached board items if available (< 10 min old).

        Returns:
            A list of raw item dicts.
        """
        if use_cache and board_id in _board_cache:
            logger.info(f"Returning {len(_board_cache[board_id])} cached items for board {board_id}")
            return _board_cache[board_id]

        all_items: list[dict] = []
        cursor: str | None = None

        while True:
            variables: dict[str, Any] = {"board_id": board_id}
            if cursor:
                variables["cursor"] = cursor

            data = await self.query(GET_BOARD_ITEMS, variables)

            boards = data.get("boards", [])
            if not boards:
                logger.warning(f"No board found with ID {board_id}")
                break

            items_page = boards[0].get("items_page", {})
            items = items_page.get("items", [])
            all_items.extend(items)

            cursor = items_page.get("cursor")
            if not cursor:
                break

        logger.info(f"Board {board_id}: fetched {len(all_items)} total items from Monday.com API")
        
        # Cache the result
        if all_items:
            _board_cache[board_id] = all_items

        return all_items

    @staticmethod
    def clear_cache(board_id: str | None = None):
        """Clear cache for a specific board or all boards."""
        if board_id:
            _board_cache.pop(board_id, None)
        else:
            _board_cache.clear()
        logger.info("Monday.com board cache cleared")

    async def get_board_columns(self, board_id: str) -> list[dict]:
        """
        Discover column IDs, titles, and types for a board.

        Args:
            board_id: The Monday.com board ID

        Returns:
            A list of column dicts: [{"id": "text0", "title": "Customer Name", "type": "text"}, ...]

        WHEN TO USE THIS:
            Run this ONCE during initial board setup to discover the
            column ID → title mapping. Then hardcode the mapping in
            column_maps.py. This is NOT called during normal runtime.

        WHY NOT AUTO-DISCOVER:
            Auto-discovery would add an extra API call on every request
            and make column mappings implicit. Explicit maps in code are:
            - Visible in code review
            - Testable without API access
            - Immune to accidental column renames breaking things silently
        """
        data = await self.query(GET_BOARD_COLUMNS, {"board_id": board_id})
        boards = data.get("boards", [])
        if not boards:
            return []
        return boards[0].get("columns", [])
