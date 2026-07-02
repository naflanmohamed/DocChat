"""
Qdrant Vector Database Implementation
=======================================
Cloud vector database — free tier at cloud.qdrant.io
Get a free cluster at: https://cloud.qdrant.io/
"""

import logging
from typing import Optional

from app.vectordb.base import VectorDBBase, SearchResult

logger = logging.getLogger(__name__)


class QdrantStore(VectorDBBase):
    """Qdrant cloud vector database implementation."""

    def __init__(
        self,
        url: str,
        api_key: str,
        collection_name: str = "documents",
        embedding_dimensions: int = 384,
    ):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self.collection_name = collection_name
        self.dimensions = embedding_dimensions

        self.client = QdrantClient(url=url, api_key=api_key)

        # Create collection if it doesn't exist
        existing = [c.name for c in self.client.get_collections().collections]
        if collection_name not in existing:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
        else:
            logger.info(f"Using existing Qdrant collection: {collection_name}")

    def upsert_chunks(self, chunks: list, embeddings: list[list[float]]) -> int:
        from qdrant_client.models import PointStruct

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=abs(hash(chunk.chunk_id)) % (2**63),  # Qdrant needs int ID
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        **chunk.metadata,
                    },
                )
            )

        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i : i + batch_size],
            )

        logger.info(f"Upserted {len(points)} chunks to Qdrant")
        return len(points)

    def search(
        self,
        query_embedding: list[float],
        user_id: str,
        top_k: int = 5,
        document_ids: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Build filter
        conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if document_ids:
            from qdrant_client.models import MatchAny
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids)
                )
            )

        query_filter = Filter(must=conditions)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k,
        )

        search_results = []
        for hit in results:
            payload = hit.payload
            search_results.append(
                SearchResult(
                    chunk_id=payload.get("chunk_id", str(hit.id)),
                    text=payload.get("text", ""),
                    score=round(hit.score, 4),
                    document_id=payload.get("document_id", ""),
                    document_name=payload.get("document_name", "Unknown"),
                    page_number=int(payload.get("page_number", 1)),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    user_id=payload.get("user_id", ""),
                )
            )

        return search_results

    def delete_document(self, document_id: str, user_id: str) -> int:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
        )
        return 0  # Qdrant doesn't return count on delete

    def get_document_chunk_count(self, document_id: str) -> int:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )
        return result.count

    def health_check(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False