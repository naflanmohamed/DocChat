"""
API Request Models
==================
Pydantic models for all incoming request bodies.

Why Pydantic models?
- Automatic validation: wrong type → clear 422 error, not a crash
- Automatic OpenAPI docs: FastAPI generates /docs from these
- Type safety: IDE shows you exactly what fields exist
- Serialization: easy to convert to/from JSON and dicts
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid


class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    """
    Request body for POST /api/chat
    
    session_id: Groups messages belonging to one conversation.
                The frontend generates this UUID when a new chat starts.
    user_id:    Identifies which user's documents to search.
                In Phase 7 (auth), this comes from the JWT token.
                For now, frontend sends it explicitly.
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question"
    )
    session_id: str = Field(
        ...,
        description="UUID identifying this conversation session"
    )
    user_id: str = Field(
        default="default_user",
        description="User identifier (for document namespace isolation)"
    )
    conversation_history: list[ChatMessage] = Field(
        default=[],
        max_length=20,   # Keep last 20 messages max (cost control)
        description="Previous messages in this conversation"
    )
    document_ids: Optional[list[str]] = Field(
        default=None,
        description="Specific document IDs to search (None = all user docs)"
    )
    
    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Question cannot be empty or whitespace only")
        return stripped


class DeleteDocumentRequest(BaseModel):
    """Request body for deleting a document."""
    document_id: str
    user_id: str = "default_user"