"""
gemini_client.py — Gemini Agent Conversation Loop (using official google-genai SDK)
====================================================================================

WHY THIS FILE EXISTS:
    This module manages the conversation between the user and Gemini using the
    official modern `google-genai` SDK (`from google import genai`).

    It supports:
      - Latest Gemini models (gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash, etc.)
      - Function calling round-trips
      - Intent-based fallback for missed tool calls
      - Conversation memory across chat turns
"""

import logging
from typing import Callable, Awaitable

from google import genai
from google.genai import types

from config import GOOGLE_API_KEY, GEMINI_MODEL
from agent.system_prompt import SYSTEM_PROMPT
from agent.tools import TOOL_SCHEMAS
from agent.intent_fallback import classify_intent, INTENT_TOOL_MAP

logger = logging.getLogger(__name__)

# Initialize the official google-genai client
client = genai.Client(api_key=GOOGLE_API_KEY)

MAX_TOOL_TURNS = 4


async def run_agent(
    user_query: str,
    conversation_history: list[dict],
    tool_handler: Callable[[str, dict], Awaitable[dict]]
) -> str:
    """
    Run the full Gemini agent loop using the google-genai SDK.

    Preserves thought signatures on model candidate responses during
    multi-turn tool calling.
    """
    # --- Step 1: Build contents list ---
    contents = _build_contents_list(conversation_history, user_query)

    # --- Step 2: Classify intent (Fallback Safety Net) ---
    intent = classify_intent(user_query)
    if intent:
        logger.info(f"Intent fallback classified query as: '{intent}'")

    # --- Step 3: Multi-turn loop ---
    fallback_used = False

    for turn in range(MAX_TOOL_TURNS):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[TOOL_SCHEMAS],
                )
            )
        except Exception as e:
            logger.error(f"Gemini API error on generate_content: {e}", exc_info=True)
            return (
                "I'm having trouble connecting to the AI service right now. "
                "Please try again in a moment."
            )

        fn_calls = _extract_function_calls(response)

        if fn_calls:
            logger.info(
                f"Turn {turn + 1}: Gemini requested {len(fn_calls)} tool call(s): "
                f"{[fc['name'] for fc in fn_calls]}"
            )

            # Preserve the model's output content (contains thought signature)
            if response.candidates and response.candidates[0].content:
                contents.append(response.candidates[0].content)

            tool_parts = []
            for fc in fn_calls:
                result = await tool_handler(fc["name"], fc["args"])
                tool_parts.append(
                    types.Part.from_function_response(
                        name=fc["name"],
                        response={"result": result}
                    )
                )

            # Append tool response turn
            contents.append(types.Content(role="user", parts=tool_parts))

        else:
            # Fallback if Gemini missed tool selection
            if intent and not fallback_used:
                fallback_used = True
                fallback_tools = INTENT_TOOL_MAP.get(intent, [])
                if fallback_tools:
                    forced_tool = fallback_tools[0]
                    logger.warning(
                        f"Applying intent fallback: forcing '{forced_tool}' (intent='{intent}')"
                    )
                    result = await tool_handler(forced_tool, {})

                    # Append forced tool call and response
                    contents.append(
                        types.Content(
                            role="model",
                            parts=[types.Part.from_function_call(name=forced_tool, args={})]
                        )
                    )
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=forced_tool,
                                    response={"result": result}
                                )
                            ]
                        )
                    )
                    continue

            # Return final text answer
            final_text = response.text or _extract_text_fallback(response)
            if final_text:
                return final_text
            break

    return "I retrieved the data but encountered an issue formatting the final answer. Please try again."


def _build_contents_list(messages: list[dict], query: str) -> list[types.Content]:
    """Build types.Content array from history and current query."""
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        genai_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(
                role=genai_role,
                parts=[types.Part.from_text(text=content)]
            )
        )
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )
    )
    return contents


def _extract_text_fallback(response) -> str:
    """Extract text from candidates if response.text is empty."""
    try:
        if response.candidates:
            parts = response.candidates[0].content.parts
            for p in parts:
                if p.text:
                    return p.text
    except Exception:
        pass
    return ""


def _build_genai_history(messages: list[dict]) -> list[types.Content]:
    """Convert conversation message dicts to google.genai Content types."""
    history = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        genai_role = "model" if role == "assistant" else "user"

        history.append(
            types.Content(
                role=genai_role,
                parts=[types.Part.from_text(text=content)]
            )
        )
    return history


def _extract_function_calls(response) -> list[dict]:
    """Extract function calls from a google-genai GenerateContentResponse."""
    calls = []
    try:
        if response.function_calls:
            for fc in response.function_calls:
                calls.append({
                    "name": fc.name,
                    "args": dict(fc.args) if fc.args else {}
                })
    except (AttributeError, TypeError) as e:
        logger.warning(f"Error extracting function calls: {e}")
    return calls
