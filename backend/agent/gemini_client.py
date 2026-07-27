"""
gemini_client.py — Gemini Agent Conversation Loop (google-genai SDK)
======================================================================

WHY THIS FILE EXISTS:
    Manages multi-turn conversation and function calling with Google Gemini
    using the official google-genai SDK.

FIX:
    Intelligent tool calling + fallback data injection that complies
    with Google's thought signature enforcement on Gemini 2.5 / 3.x models.
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

# Initialize official google-genai client
client = genai.Client(api_key=GOOGLE_API_KEY)

MAX_TOOL_TURNS = 4


async def run_agent(
    user_query: str,
    conversation_history: list[dict],
    tool_handler: Callable[[str, dict], Awaitable[dict]]
) -> str:
    """
    Run the Gemini agent loop for a user query.
    """
    contents = _build_contents_list(conversation_history, user_query)
    intent = classify_intent(user_query)

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

            # Preserve model candidate content (thought signature)
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

            contents.append(types.Content(role="user", parts=tool_parts))

        else:
            # If Gemini returned text without calling a tool, but we detected a data intent
            if intent:
                fallback_tools = INTENT_TOOL_MAP.get(intent, [])
                if fallback_tools:
                    forced_tool = fallback_tools[0]
                    logger.info(
                        f"Applying fallback data injection for intent '{intent}' -> '{forced_tool}'"
                    )
                    result = await tool_handler(forced_tool, {})
                    
                    # Inject pre-calculated result directly into context
                    context_query = (
                        f"User question: {user_query}\n\n"
                        f"Retrieved Business Data for {forced_tool}:\n"
                        f"{result}"
                    )
                    try:
                        fallback_resp = client.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=context_query,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                            )
                        )
                        if fallback_resp.text:
                            return fallback_resp.text
                    except Exception as e:
                        logger.error(f"Fallback generation error: {e}")

            # Return Gemini's text response
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


def _extract_function_calls(response) -> list[dict]:
    """Extract function calls from a google-genai response."""
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
