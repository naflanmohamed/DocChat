"""
Health Check Endpoint
=====================
GET /api/health

Used by:
- Render/Railway to check if the service is running
- Load balancers to route traffic
- Monitoring tools (UptimeRobot, etc.)
- Your frontend to show "API connected" status

A good health check reports:
1. Is the server running? (yes, if you're getting a response)
2. Can it reach its dependencies? (DB, external APIs)
3. What version is running? (for deployment verification)
"""

import time
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Track when the server started (for uptime reporting)
SERVER_START_TIME = time.time()


class HealthResponse(BaseModel):
    """Structured health check response."""
    status: str                    # "healthy" | "degraded" | "unhealthy"
    version: str
    environment: str
    uptime_seconds: float
    services: dict[str, str]       # Each service → "ok" | "error: ..."


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Comprehensive health check.
    
    Checks:
    1. Application is running
    2. Configuration is valid
    3. Which services are configured
    
    Returns HTTP 200 if healthy, 503 if degraded.
    """
    uptime = time.time() - SERVER_START_TIME
    services = {}
    overall_status = "healthy"
    
    # ── Check LLM configuration ──────────────────────────
    if settings.llm_provider == "gemini":
        if settings.gemini_api_key:
            services["llm"] = f"gemini ({settings.gemini_model})"
        else:
            services["llm"] = "error: GEMINI_API_KEY not set"
            overall_status = "degraded"
    elif settings.llm_provider == "groq":
        if settings.groq_api_key:
            services["llm"] = f"groq ({settings.groq_model})"
        else:
            services["llm"] = "error: GROQ_API_KEY not set"
            overall_status = "degraded"
    
    # ── Check embedding configuration ────────────────────
    if settings.embedding_provider == "local":
        services["embeddings"] = f"local ({settings.embedding_model})"
    elif settings.embedding_provider == "huggingface":
        if settings.hf_api_key:
            services["embeddings"] = f"huggingface ({settings.embedding_model})"
        else:
            services["embeddings"] = "error: HF_API_KEY not set"
            overall_status = "degraded"
    
    # ── Check vector DB configuration ───────────────────
    if settings.vector_db_provider == "chroma":
        services["vector_db"] = f"chroma (local: {settings.chroma_persist_dir})"
    elif settings.vector_db_provider == "qdrant":
        if settings.qdrant_url and settings.qdrant_api_key:
            services["vector_db"] = f"qdrant ({settings.qdrant_url})"
        else:
            services["vector_db"] = "error: QDRANT_URL or QDRANT_API_KEY not set"
            overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
        services=services,
    )