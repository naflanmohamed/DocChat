"""
FastAPI Application Entry Point
================================
This is where the FastAPI app is created and configured.

Key concepts demonstrated:
- Lifespan events (startup/shutdown) — replaces deprecated @app.on_event
- CORS middleware — allows the Next.js frontend to call this API
- Router inclusion — keeps routes organized in separate files
- Global error handlers — consistent error responses
- Startup validation — fail fast with clear messages
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

# Configure logging — critical for debugging in production
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — runs code at startup and shutdown.
    
    This is the modern FastAPI pattern (replaces @app.on_event).
    Code before 'yield' runs at startup.
    Code after 'yield' runs at shutdown.
    
    Why do startup checks?
    - "Fail fast" principle: better to crash immediately with a
      clear error than to silently fail on the first API request
    - Creates required directories before any request arrives
    - Validates all API keys are present
    """
    # ── STARTUP ────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Embedding Provider: {settings.embedding_provider}")
    logger.info(f"Vector DB: {settings.vector_db_provider}")
    logger.info("=" * 50)
    
    # Validate required settings — fail fast
    errors = settings.validate_for_startup()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise RuntimeError(
            f"Cannot start: {len(errors)} configuration error(s). "
            "Check the logs above."
        )
    
    # Create required directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info(f"Upload directory ready: {settings.upload_dir}")
    
    if settings.vector_db_provider == "chroma":
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        logger.info(f"Chroma directory ready: {settings.chroma_persist_dir}")
    
    logger.info("Startup complete — ready to accept requests")
    
    yield  # Application runs here
    
    # ── SHUTDOWN ───────────────────────────────────────────
    logger.info("Shutting down...")
    # Add cleanup here if needed (close DB connections, etc.)
    logger.info("Shutdown complete")


# ── Create FastAPI Application ──────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    A production-ready RAG (Retrieval-Augmented Generation) chatbot API.
    
    Upload PDF, DOCX, and TXT documents, then chat with them.
    All answers include citations showing which document sections were used.
    
    ## Features
    - Document upload (PDF, DOCX, TXT)
    - Semantic search using embeddings
    - AI-generated answers with source citations
    - Streaming responses
    - Multiple document support
    """,
    docs_url="/docs",        # Swagger UI at /docs
    redoc_url="/redoc",      # ReDoc UI at /redoc
    openapi_url="/openapi.json",
    lifespan=lifespan,       # Use the lifespan context manager
)


# ── CORS Middleware ──────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Without this, browsers block requests from localhost:3000 → localhost:8000
# The browser enforces CORS — it's NOT a server-side security feature
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler.
    
    Without this, unhandled exceptions return a raw 500 error with
    Python traceback details — which leaks implementation details.
    
    This returns a clean JSON error with a request ID for tracing.
    In production, you'd log to a service like Sentry here.
    """
    logger.exception(f"Unhandled exception on {request.method} {request.url}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
            "detail": str(exc) if settings.debug else None,
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors with a 400 response."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": str(exc),
        }
    )


# ── Include Routers ──────────────────────────────────────────
# Each router handles a group of related endpoints.
# We import them here so main.py stays clean.
# These will be filled in Phase 3.
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router

app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(upload_router, prefix="/api", tags=["Documents"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(documents_router, prefix="/api", tags=["Documents"])


# ── Root Endpoint ────────────────────────────────────────────
@app.get("/")
async def root():
    """
    Root endpoint — useful for checking the API is alive.
    Railway and Render use this for health checks.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }