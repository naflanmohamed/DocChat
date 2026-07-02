"""
Chat API Endpoint
=================
POST /api/chat

Receives a question, runs the RAG pipeline,
returns an answer with citations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.core.embeddings import get_embedder
from app.core.rag_chain import RAGChain
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse, Citation
from app.vectordb.factory import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Answer a question using the RAG pipeline.

    The question is embedded, relevant document chunks retrieved,
    and a grounded answer generated with source citations.
    """
    logger.info(
        f"Chat request: user='{request.user_id}' "
        f"session='{request.session_id}' "
        f"question='{request.question[:60]}...'"
    )

    try:
        # Initialise embedder
        embedder = get_embedder(
            provider=settings.embedding_provider,
            model_name=settings.embedding_model,
            hf_api_key=settings.hf_api_key,
        )

        # Initialise vector store
        vector_store = get_vector_store(
            provider=settings.vector_db_provider,
            chroma_persist_dir=settings.chroma_persist_dir,
            chroma_collection_name=settings.chroma_collection_name,
            qdrant_url=settings.qdrant_url,
            qdrant_api_key=settings.qdrant_api_key,
            qdrant_collection_name=settings.qdrant_collection_name,
            embedding_dimensions=settings.embedding_dimensions,
        )

        # Initialise RAG chain
        rag_chain = RAGChain(
            embedder=embedder,
            vector_store=vector_store,
            llm_provider=settings.llm_provider,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            groq_api_key=settings.groq_api_key,
            groq_model=settings.groq_model,
            max_retrieval_docs=settings.max_retrieval_docs,
            min_relevance_score=settings.min_relevance_score,
        )

        # Run RAG pipeline
        rag_response = rag_chain.query(
            question=request.question,
            user_id=request.user_id,
            conversation_history=[
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ],
            document_ids=request.document_ids,
        )

        # Convert citations to response model
        citations = [
            Citation(
                source_id=chunk.chunk_id,
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                relevance_score=chunk.score,
                excerpt=chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text,
            )
            for chunk in rag_response.citations
        ]

        return ChatResponse(
            answer=rag_response.answer,
            citations=citations,
            session_id=request.session_id,
            model_used=rag_response.model_used,
            retrieval_count=len(rag_response.all_retrieved),
            has_relevant_sources=rag_response.has_relevant_sources,
        )

    except RuntimeError as e:
        logger.error(f"RAG pipeline error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in chat endpoint")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        )