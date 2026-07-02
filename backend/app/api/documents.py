"""
Documents API Endpoint
======================
GET  /api/documents        — List all documents for a user
GET  /api/documents/{id}   — Get status of one document
DELETE /api/documents/{id} — Delete a document
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime

from app.config import Settings, get_settings
from app.models.responses import DocumentStatus, DocumentListResponse
from app.api.upload import get_document_status, _document_store
from app.vectordb.factory import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = Query(default="default_user"),
    settings: Settings = Depends(get_settings),
):
    """List all documents uploaded by a user."""
    user_docs = [
        doc for doc in _document_store.values()
        if doc.get("user_id") == user_id
    ]

    # Sort by created_at descending (newest first)
    user_docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)

    documents = []
    for doc in user_docs:
        documents.append(
            DocumentStatus(
                document_id=doc["document_id"],
                filename=doc["filename"],
                status=doc["status"],
                chunk_count=doc.get("chunk_count"),
                error_message=doc.get("error_message"),
                created_at=datetime.fromisoformat(doc["created_at"]),
                file_size_bytes=doc.get("file_size_bytes", 0),
            )
        )

    return DocumentListResponse(
        documents=documents,
        total_count=len(documents),
    )


@router.get("/documents/{document_id}", response_model=DocumentStatus)
async def get_document(
    document_id: str,
    settings: Settings = Depends(get_settings),
):
    """Get the status of a specific document."""
    doc = get_document_status(document_id)

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found"
        )

    return DocumentStatus(
        document_id=doc["document_id"],
        filename=doc["filename"],
        status=doc["status"],
        chunk_count=doc.get("chunk_count"),
        error_message=doc.get("error_message"),
        created_at=datetime.fromisoformat(doc["created_at"]),
        file_size_bytes=doc.get("file_size_bytes", 0),
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Query(default="default_user"),
    settings: Settings = Depends(get_settings),
):
    """Delete a document and all its vectors from the database."""
    doc = get_document_status(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.get("user_id") != user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this document"
        )

    # Delete from vector store
    vector_store = get_vector_store(
        provider=settings.vector_db_provider,
        chroma_persist_dir=settings.chroma_persist_dir,
        chroma_collection_name=settings.chroma_collection_name,
        qdrant_url=settings.qdrant_url,
        qdrant_api_key=settings.qdrant_api_key,
        qdrant_collection_name=settings.qdrant_collection_name,
        embedding_dimensions=settings.embedding_dimensions,
    )

    deleted_count = vector_store.delete_document(document_id, user_id)

    # Remove from in-memory store
    _document_store.pop(document_id, None)

    logger.info(f"Deleted document {document_id}: {deleted_count} chunks removed")

    return {
        "message": f"Document deleted successfully",
        "document_id": document_id,
        "chunks_deleted": deleted_count,
    }