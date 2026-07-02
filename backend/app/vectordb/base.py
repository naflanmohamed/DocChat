"""
Vector Database Abstract Base Class
=====================================
Defines the interface every vector DB implementation must follow.

This is the Strategy Pattern:
- VectorDBBase defines WHAT operations are available
- ChromaStore and QdrantStore define HOW they're done
- The rest of the app only imports VectorDBBase

Result: you can switch from Chroma to Qdrant by changing
one environment variable. Zero other code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """
    One result from a vector similarity search.
    This is the data that flows from vector DB → prompt assembly → citations.
    """
    chunk_id: str           # Vector DB record ID
    text: str               # The chunk text
    score: float            # Cosine similarity (0-1, higher = more relevant)
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    user_id: str


class VectorDBBase(ABC):
    """Abstract interface for vector database operations."""

    @abstractmethod
    def upsert_chunks(
        self,
        chunks: list,           # list[DocumentChunk]
        embeddings: list[list[float]],
    ) -> int:
        """
        Store chunks with their embeddings.
        Returns the number of chunks stored.
        'upsert' = insert if new, update if exists (by chunk_id)
        """
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        user_id: str,
        top_k: int = 5,
        document_ids: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """
        Find the most similar chunks to a query embedding.

        user_id: Only search this user's documents
        top_k: Return this many results
        document_ids: If provided, only search these specific documents
        """
        ...

    @abstractmethod
    def delete_document(self, document_id: str, user_id: str) -> int:
        """
        Delete all chunks belonging to a document.
        Returns number of chunks deleted.
        """
        ...

    @abstractmethod
    def get_document_chunk_count(self, document_id: str) -> int:
        """Return how many chunks a document has in the DB."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the DB is reachable and healthy."""
        ...