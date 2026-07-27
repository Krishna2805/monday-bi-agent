"""
main.py — FastAPI Application Entry Point
==========================================

WHY THIS FILE EXISTS:
    This is the single entry point for the entire backend API.
    FastAPI is chosen because:
      1. It's async-native — our Monday.com API calls and Groq LLM calls
         are all I/O-bound, so async gives us concurrency without threads
      2. It auto-generates OpenAPI docs at /docs (useful for debugging)
      3. Pydantic integration for request/response validation
      4. Built-in CORS middleware for frontend communication

API ENDPOINTS:
    GET  /health — Health check & model verification
    POST /chat   — Main conversational BI agent endpoint

HOW TO RUN:
    uvicorn main:app --reload --port 8000
"""

import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import LLM_MODEL
from models import ChatRequest, ChatResponse
from agent.groq_client import run_agent
from agent.tool_handler import handle_tool_call

# Configure logging format for production visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- App Initialization ---
app = FastAPI(
    title="Monday.com BI Agent",
    description="Business Intelligence agent powered by Groq Llama 3.3 70B, backed by Monday.com data",
    version="0.1.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",           # Vite dev server (local development)
        "https://your-app.vercel.app",     # Production frontend (update after deploy)
        "*"                                # Permissive for prototype testing
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Root Welcome Endpoint ---
@app.get("/")
async def root():
    """
    Root API endpoint welcome message.
    Redirects/instructs developer to /docs and /health.
    """
    return {
        "message": "Monday.com BI Agent API is active",
        "health": "/health",
        "docs": "/docs"
    }


# --- Health Check Endpoint ---
@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns status and configured LLM model name.
    """
    return {
        "status": "ok",
        "model": LLM_MODEL
    }


# --- Chat Endpoint ---
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main BI agent conversational endpoint.

    Accepts a list of conversation messages (last message is current query).
    Orchestrates Groq LLM tool selection, Monday.com data retrieval,
    normalization, and deterministic analytics, returning the agent's natural
    language explanation.

    Args:
        request: ChatRequest object containing messages array

    Returns:
        ChatResponse object containing the agent's reply
    """
    try:
        # Extract messages list from request
        raw_messages = request.messages

        # The last message is the current user question
        current_query = raw_messages[-1].content
        logger.info(f"Received query: '{current_query}'")

        # All earlier messages form the conversation history passed to the LLM agent
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in raw_messages[:-1]
        ]

        # Execute the Groq Llama 3.3 70B agent loop
        reply = await run_agent(
            user_query=current_query,
            conversation_history=conversation_history,
            tool_handler=handle_tool_call
        )

        return ChatResponse(reply=reply)

    except Exception as e:
        logger.error(f"Error processing /chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )


# --- Streaming Chat Endpoint (SSE) ---
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming BI agent endpoint (Server-Sent Events).

    Streams chunks of the agent response as text/event-stream for
    real-time word-by-word response rendering in the frontend UI.
    """
    raw_messages = request.messages
    current_query = raw_messages[-1].content
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in raw_messages[:-1]
    ]

    async def event_generator():
        try:
            full_reply = await run_agent(
                user_query=current_query,
                conversation_history=conversation_history,
                tool_handler=handle_tool_call
            )
            # Stream in word/phrase chunks for smooth UI streaming animation
            words = full_reply.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + " "
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.02)
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: ⚠️ Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
