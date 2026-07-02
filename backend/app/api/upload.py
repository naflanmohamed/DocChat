"""
Upload API Endpoint
===================
POST /api/upload

Accepts a file upload, processes it in the background,
and returns immediately with a document_id.

Why background processing?
- A 50-page PDF can take 10-30 seconds to process
- HTTP requests time out after ~30 seconds
- Background tasks let us return instantly and process async
- Frontend polls /api/documents/{id} to check progress
"""

import logging
import os
import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.core.document_processor import DocumentProcessor
from app.core.chunker import DocumentChunker
from app.core.embeddings import get_embedder
from app.models.responses import UploadResponse, DocumentStatus
from app.utils.file_utils import (
    generate_document_id,
    get_file_extension,
    is_allowed_extension,
    get_unique_filepath,
)
from app.vectordb.factory import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory document status store
# In production (Phase 7+), this would be a database (PostgreSQL/Redis)
# For now, a dict is sufficient for a single-server deployment
_document_store: dict[str, dict] = {}


def get_document_status(document_id: str) -> dict | None:
    """Get current status of a document by ID."""
    return _document_store.get(document_id)


def set_document_status(document_id: str, status_data: dict):
    """Update document status."""
    _document_store[document_id] = status_data


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(default="default_user"),
    session_id: str = Form(default=""),
    settings: Settings = Depends(get_settings),
):
    """
    Upload a document for processing.

    Accepts: PDF, DOCX, TXT files up to 50MB
    Returns: document_id immediately, processing happens in background

    The frontend should poll GET /api/documents to check when
    status changes from "processing" to "ready".
    """
    # ── Validate file ────────────────────────────────────────

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = get_file_extension(file.filename)
    if not is_allowed_extension(file.filename, settings.allowed_extensions_list):
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type '.{ext}' not allowed. "
                f"Allowed types: {', '.join(settings.allowed_extensions_list)}"
            ),
        )

    # Read file content to check size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {file_size / (1024*1024):.1f}MB. "
                f"Maximum: {settings.max_file_size_mb}MB"
            ),
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # ── Generate document ID and save file ───────────────────

    document_id = generate_document_id(file.filename, user_id)
    file_path = get_unique_filepath(settings.upload_dir, file.filename)

    # Save the uploaded file to disk
    with open(file_path, "wb") as f:
        f.write(file_content)

    logger.info(
        f"File saved: {file.filename} ({file_size / 1024:.1f}KB) "
        f"→ {file_path} (doc_id: {document_id})"
    )

    # ── Store initial status ─────────────────────────────────

    set_document_status(document_id, {
        "document_id": document_id,
        "filename": file.filename,
        "status": "processing",
        "chunk_count": None,
        "error_message": None,
        "created_at": datetime.utcnow().isoformat(),
        "file_size_bytes": file_size,
        "user_id": user_id,
    })

    # ── Queue background processing ──────────────────────────
    # This runs AFTER the HTTP response is sent to the client.
    # The client gets the response immediately, while processing happens.

    background_tasks.add_task(
        process_document_background,
        file_path=file_path,
        filename=file.filename,
        document_id=document_id,
        user_id=user_id,
        settings=settings,
    )

    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        message=(
            f"Document '{file.filename}' received and queued for processing. "
            "Poll GET /api/documents to check when it's ready."
        ),
    )


async def process_document_background(
    file_path: str,
    filename: str,
    document_id: str,
    user_id: str,
    settings: Settings,
):
    """
    Background task: process document and store in vector DB.

    This runs asynchronously after the upload response is sent.
    Updates _document_store so the frontend can poll for progress.

    Steps:
    1. Extract text from file
    2. Chunk the text
    3. Embed all chunks
    4. Store in vector DB
    5. Update status to "ready"
    """
    start_time = time.time()
    logger.info(f"Background processing started: {filename} ({document_id})")

    try:
        # Step 1: Extract text
        logger.info(f"[{document_id}] Step 1/4: Extracting text from {filename}")
        processor = DocumentProcessor()
        extracted = processor.process(file_path=file_path, filename=filename)

        if extracted.error:
            raise RuntimeError(f"Text extraction failed: {extracted.error}")

        if extracted.is_empty:
            raise RuntimeError(
                f"No text could be extracted from {filename}. "
                "The file may be empty or contain only images."
            )

        logger.info(
            f"[{document_id}] Extracted {extracted.total_chars:,} chars "
            f"from {extracted.total_pages} pages"
        )

        # Step 2: Chunk the text
        logger.info(f"[{document_id}] Step 2/4: Chunking text")
        chunker = DocumentChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = chunker.chunk(
            extracted_doc=extracted,
            document_id=document_id,
            user_id=user_id,
        )

        if not chunks:
            raise RuntimeError("No chunks produced — document may be too short")

        logger.info(f"[{document_id}] Created {len(chunks)} chunks")

        # Step 3: Embed chunks
        logger.info(f"[{document_id}] Step 3/4: Generating embeddings for {len(chunks)} chunks")
        embedder = get_embedder(
            provider=settings.embedding_provider,
            model_name=settings.embedding_model,
            hf_api_key=settings.hf_api_key,
        )

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_texts(chunk_texts)

        logger.info(
            f"[{document_id}] Generated {len(embeddings)} embeddings "
            f"({embedder.dimensions} dimensions each)"
        )

        # Step 4: Store in vector DB
        logger.info(f"[{document_id}] Step 4/4: Storing in vector database")
        vector_store = get_vector_store(
            provider=settings.vector_db_provider,
            chroma_persist_dir=settings.chroma_persist_dir,
            chroma_collection_name=settings.chroma_collection_name,
            qdrant_url=settings.qdrant_url,
            qdrant_api_key=settings.qdrant_api_key,
            qdrant_collection_name=settings.qdrant_collection_name,
            embedding_dimensions=settings.embedding_dimensions,
        )

        stored_count = vector_store.upsert_chunks(chunks, embeddings)

        elapsed = time.time() - start_time
        logger.info(
            f"[{document_id}] Processing complete in {elapsed:.1f}s: "
            f"{stored_count} chunks stored"
        )

        # Update status to ready
        set_document_status(document_id, {
            **get_document_status(document_id),
            "status": "ready",
            "chunk_count": stored_count,
            "processing_time_seconds": round(elapsed, 2),
        })

    except Exception as e:
        logger.exception(f"[{document_id}] Background processing failed: {e}")
        set_document_status(document_id, {
            **(_document_store.get(document_id) or {}),
            "status": "error",
            "error_message": str(e),
        })
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")