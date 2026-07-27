"""
models.py — Pydantic Request & Response Data Models
===================================================

WHY THIS FILE EXISTS:
    FastAPI relies on Pydantic models for:
      1. Request body parsing and automatic JSON validation
      2. Auto-generated API documentation (Swagger UI at /docs)
      3. Type safety and runtime data integrity
      4. Structured error responses if the frontend sends invalid JSON

    This module defines the contract between the React frontend and
    the FastAPI backend for the /chat endpoint.

MODEL DESCRIPTIONS:

    Message:
        Represents a single message in the chat conversation history.
        - role: "user" or "assistant"
        - content: The text of the message

    ChatRequest:
        The payload sent by the frontend on POST /chat.
        Contains the full message history (including the latest question).
        Example:
        {
            "messages": [
                {"role": "user", "content": "How is Mining pipeline?"},
                {"role": "assistant", "content": "The Mining pipeline has..."},
                {"role": "user", "content": "What about Renewables?"}
            ]
        }

    ChatResponse:
        The response returned to the frontend.
        Contains the BI agent's final text answer.
        Example:
        {
            "reply": "The Renewables pipeline is worth ₹2.1 Cr across..."
        }
"""

from typing import Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    A single message in the conversation history.

    Attributes:
        role: "user" (question) or "assistant" (agent response)
        content: The text message content
    """
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Message sender role: 'user' or 'assistant'"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="The message text content (cannot be empty)"
    )


class ChatRequest(BaseModel):
    """
    Request payload for POST /chat.

    Attributes:
        messages: Non-empty list of conversation messages.
                  The LAST message in the array is treated as the
                  current user query; earlier messages are history.
    """
    messages: list[Message] = Field(
        ...,
        min_items=1,
        description="Full conversation message history. Last element is the current query."
    )


class ChatResponse(BaseModel):
    """
    Response payload for POST /chat.

    Attributes:
        reply: The agent's natural language response
    """
    reply: str = Field(
        ...,
        description="The BI agent's natural language answer"
    )
