"""
Chroma Vector Database Implementation
======================================
Local vector database — no cloud account needed.
Data persists to disk in the chroma_db/ directory.

Chroma concepts:
- Collection: like a table in SQL. We use one collection per app.
- Document: Chroma's term for a stored record (not our PDF document)
- IDs: must be unique strings — we use chunk_id
- Embeddings: the vectors
- Documents: the text (Chroma calls text "documents")
- Metadatas: the metadata dict

Filtering: Chroma supports metadata filtering using a
where clause. We filter by user_id so users only see
their own documents.
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.vectordb.base import VectorDBBase, SearchResult

logger = logging.getLogger(__name__)


class ChromaStore(VectorDBBase):
    """
    Chroma vector database implementation.

    Usage:
        store = ChromaStore(persist_dir="./chroma_db", collection_name="documents")
        store.upsert_chunks(chunks, embeddings)
        results = store.search(query_vector, user_id="user1", top_k=5)
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "documents",
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        # Create persistent Chroma client
        # Data survives restarts — stored in persist_dir/
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,  # Don't send usage data to Chroma
            ),
        )

        # Get or create our collection
        # If collection exists, loads it. If not, creates it.
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",  # Use cosine similarity (not L2)
            },
        )

        logger.info(
            f"ChromaStore initialized: {persist_dir}/{collection_name} "
            f"({self.collection.count()} existing records)"
        )

    def upsert_chunks(
        self,
        chunks: list,
        embeddings: list[list[float]],
    ) -> int:
        """
        Store chunks with their embeddings in Chroma.

        We use upsert (not add) so re-uploading a document
        replaces old chunks rather than duplicating them.
        """
        if not chunks:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "must have the same length"
            )

        # Prepare data in Chroma's format
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # Chroma upsert: insert new, update existing (by id)
        # Process in batches of 100 to avoid memory issues
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_docs = documents[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]

            self.collection.upsert(
                ids=batch_ids,
                embeddings=batch_embs,
                documents=batch_docs,
                metadatas=batch_metas,
            )
            total_upserted += len(batch_ids)
            logger.debug(f"Upserted batch {i//batch_size + 1}: {len(batch_ids)} chunks")

        logger.info(f"Upserted {total_upserted} chunks to Chroma")
        return total_upserted

    def search(
        self,
        query_embedding: list[float],
        user_id: str,
        top_k: int = 5,
        document_ids: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """
        Find most similar chunks using cosine similarity.

        Chroma's where clause filters metadata BEFORE the vector search.
        This is efficient — Chroma doesn't search other users' vectors.
        """
        # Build metadata filter
        # Chroma uses MongoDB-style filter syntax
        if document_ids:
            where = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"document_id": {"$in": document_ids}},
                ]
            }
        else:
            where = {"user_id": {"$eq": user_id}}

        # Check if we have any documents for this user
        # Chroma throws an error if you query an empty collection
        total_records = self.collection.count()
        if total_records == 0:
            logger.warning("Vector store is empty — no documents uploaded yet")
            return []

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, total_records),  # Can't return more than exists
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Chroma query failed: {e}")
            return []

        search_results = []
        ids = results["ids"][0]           # [0] because we sent one query
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i, (chunk_id, text, meta, distance) in enumerate(
            zip(ids, documents, metadatas, distances)
        ):
            # Chroma returns cosine DISTANCE (0=identical, 2=opposite)
            # Convert to similarity score (1=identical, 0=unrelated)
            similarity_score = 1 - (distance / 2)

            search_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    text=text,
                    score=round(similarity_score, 4),
                    document_id=meta.get("document_id", ""),
                    document_name=meta.get("document_name", "Unknown"),
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    user_id=meta.get("user_id", ""),
                )
            )

        # Sort by score descending (highest similarity first)
        search_results.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            f"Search returned {len(search_results)} results "
            f"(top score: {search_results[0].score:.3f if search_results else 'N/A'})"
        )

        return search_results

    def delete_document(self, document_id: str, user_id: str) -> int:
        """Delete all chunks belonging to a document."""
        # Find all chunk IDs for this document
        results = self.collection.get(
            where={
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"user_id": {"$eq": user_id}},
                ]
            },
            include=[],  # Just get IDs, no text needed
        )

        ids_to_delete = results["ids"]
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            logger.info(
                f"Deleted {len(ids_to_delete)} chunks for "
                f"document {document_id}"
            )
        return len(ids_to_delete)

    def get_document_chunk_count(self, document_id: str) -> int:
        """Count chunks for a specific document."""
        results = self.collection.get(
            where={"document_id": {"$eq": document_id}},
            include=[],
        )
        return len(results["ids"])

    def health_check(self) -> bool:
        """Check if Chroma is operational."""
        try:
            self.collection.count()
            return True
        except Exception as e:
            logger.error(f"Chroma health check failed: {e}")
            return False