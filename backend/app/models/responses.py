"""
API Response Models
===================
Pydantic models for all API responses.

Using response models gives you:
- Consistent JSON structure across all endpoints
- Automatic field filtering (don't accidentally return passwords)
- OpenAPI docs shows exactly what clients receive
- Type safety in tests
"""

from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Citation(BaseModel):
    """
    A single source citation.
    
    When the LLM answers "Q3 revenue was $4.2M [Source 1]",
    the frontend uses this model to render the citation card
    showing which file and page that came from.
    """
    source_id: str              # Unique ID of this chunk in vector DB
    document_name: str          # Original filename e.g. "annual_report.pdf"
    page_number: Optional[int]  # Page in the document (None for TXT files)
    chunk_index: int            # Which chunk within the document
    relevance_score: float      # Cosine similarity score (0-1)
    excerpt: str                # The actual text chunk that was retrieved


class ChatResponse(BaseModel):
    """Response from POST /api/chat"""
    answer: str                         # The LLM's answer text
    citations: list[Citation]           # Sources used to generate the answer
    session_id: str                     # Echo back the session ID
    model_used: str                     # Which LLM was used
    retrieval_count: int                # How many chunks were retrieved
    has_relevant_sources: bool          # Were relevant sources found?


class DocumentStatus(BaseModel):
    """Status of an uploaded document."""
    document_id: str
    filename: str
    status: str    # "processing" | "ready" | "error"
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    file_size_bytes: int


class UploadResponse(BaseModel):
    """Response from POST /api/upload"""
    document_id: str
    filename: str
    status: str          # "processing" (background task started)
    message: str


class DocumentListResponse(BaseModel):
    """Response from GET /api/documents"""
    documents: list[DocumentStatus]
    total_count: int


class ErrorResponse(BaseModel):
    """Standard error response shape."""
    error: str           # Machine-readable error code
    message: str         # Human-readable message
    detail: Optional[Any] = None  # Extra context (only in debug mode)