"""
Vector DB Factory
=================
Returns the configured vector database implementation.
"""

import logging
from app.vectordb.base import VectorDBBase

logger = logging.getLogger(__name__)


def get_vector_store(
    provider: str = "chroma",
    chroma_persist_dir: str = "./chroma_db",
    chroma_collection_name: str = "documents",
    qdrant_url: str = "",
    qdrant_api_key: str = "",
    qdrant_collection_name: str = "documents",
    embedding_dimensions: int = 384,
) -> VectorDBBase:
    """
    Factory function — returns the configured vector store.
    Called once at startup, reused for all requests.
    """
    if provider == "chroma":
        from app.vectordb.chroma_store import ChromaStore
        logger.info(f"Using Chroma vector store at {chroma_persist_dir}")
        return ChromaStore(
            persist_dir=chroma_persist_dir,
            collection_name=chroma_collection_name,
        )

    elif provider == "qdrant":
        from app.vectordb.qdrant_store import QdrantStore
        logger.info(f"Using Qdrant vector store at {qdrant_url}")
        return QdrantStore(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=qdrant_collection_name,
            embedding_dimensions=embedding_dimensions,
        )

    else:
        raise ValueError(
            f"Unknown vector DB provider: {provider}. "
            "Use 'chroma' or 'qdrant'"
        )