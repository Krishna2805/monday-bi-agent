"""
groq_client.py — Ultra-Fast Groq LLM Inference Engine (Llama 3.3 70B)
======================================================================

WHY THIS FILE EXISTS:
    Executes conversational BI agent queries using Groq's high-speed
    Llama 3.3 70B inference engine (`llama-3.3-70b-versatile`).

    Provides:
      - ~300ms ultra-fast response times
      - High rate-limit headroom with zero quota crashes
      - Clean natural language formatting over Monday.com analytics payloads
"""

import logging
from typing import Callable, Awaitable

from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL
from agent.system_prompt import SYSTEM_PROMPT
from agent.intent_fallback import classify_intent, INTENT_TOOL_MAP

logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)


async def run_agent(
    user_query: str,
    conversation_history: list[dict],
    tool_handler: Callable[[str, dict], Awaitable[dict]]
) -> str:
    """
    Run the BI agent loop using Groq Llama 3.3 70B.

    Args:
        user_query: The user's question
        conversation_history: List of message dicts [{"role": "user"/"assistant", "content": "..."}]
        tool_handler: Async callback for handling Monday.com data retrieval & analytics

    Returns:
        Ultra-fast natural language explanation of the business data
    """
    try:
        # --- Step 1: Intent Classification ---
        intent = classify_intent(user_query) or "pipeline"
        target_tools = INTENT_TOOL_MAP.get(intent, ["query_deals"])
        primary_tool = target_tools[0]

        logger.info(f"Groq Llama 3.3 70B Agent: query='{user_query[:40]}...' -> intent='{intent}' -> tool='{primary_tool}'")

        # --- Step 2: Retrieve Live Monday.com Data & Deterministic Analytics ---
        data_summary = await tool_handler(primary_tool, {})

        # --- Step 3: Build Messages Array for Groq ---
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Append conversation history for follow-up context
        for msg in conversation_history:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": msg.get("content", "")})

        # Append user query + retrieved business metrics
        prompt_with_data = (
            f"User Question: {user_query}\n\n"
            f"[Live Monday.com Data Payload for {primary_tool}]:\n"
            f"{data_summary}\n\n"
            f"Instruction: Translate the pre-calculated metrics above into a clear, concise executive answer. "
            f"Always include any ⚠️ Data note: caveats present in the payload."
        )
        messages.append({"role": "user", "content": prompt_with_data})

        # --- Step 4: Execute Groq Llama 3.3 70B Generation ---
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )

        reply = completion.choices[0].message.content
        return reply

    except Exception as e:
        logger.error(f"Groq LLM error: {e}", exc_info=True)
        return f"⚠️ Error generating response: {str(e)[:150]}"
