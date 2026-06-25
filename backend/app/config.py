"""
Application Configuration
=========================
Uses Pydantic Settings to read from environment variables.
All settings are type-validated automatically.

Why Pydantic Settings?
- Type safety: CHUNK_SIZE="abc" raises a clear error, not a silent bug
- Validation: can enforce min/max values, patterns, etc.
- Defaults: sensible defaults mean less required configuration
- IDE support: autocomplete works on settings.chunk_size
- Single source of truth: all config in one place
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings loaded from environment variables.
    
    Pydantic automatically:
    - Reads from .env file (via model_config)
    - Validates types (str, int, bool, etc.)
    - Raises clear errors for missing required fields
    - Provides defaults for optional fields
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env file
        env_file_encoding="utf-8",
        case_sensitive=False,      # CHUNK_SIZE == chunk_size
        extra="ignore",            # Ignore unknown env vars
    )
    
    # ── Application ──────────────────────────────────────────
    app_name: str = "Document RAG Chatbot"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # ── CORS ─────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Convert comma-separated string to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    # ── LLM Provider ─────────────────────────────────────────
    llm_provider: Literal["gemini", "groq"] = "gemini"
    
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    
    # ── Embeddings ───────────────────────────────────────────
    embedding_provider: Literal["huggingface", "local"] = "local"
    hf_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Embedding dimensions depend on model:
    # all-MiniLM-L6-v2    → 384 dimensions
    # all-mpnet-base-v2   → 768 dimensions
    # BAAI/bge-small-en   → 384 dimensions
    embedding_dimensions: int = 384
    
    # ── Vector Database ──────────────────────────────────────
    vector_db_provider: Literal["chroma", "qdrant"] = "chroma"
    
    # Chroma settings
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "documents"
    
    # Qdrant settings
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "documents"
    
    # ── File Upload ──────────────────────────────────────────
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    allowed_extensions: str = "pdf,docx,txt"
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]
    
    # ── RAG Settings ─────────────────────────────────────────
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=200, ge=0, le=500)
    max_retrieval_docs: int = Field(default=5, ge=1, le=20)
    min_relevance_score: float = Field(default=0.3, ge=0.0, le=1.0)
    
    # ── Security ─────────────────────────────────────────────
    secret_key: str = "dev-secret-change-in-production"
    api_key_header: str = "X-API-Key"
    
    # ── Validators ───────────────────────────────────────────
    @field_validator("chunk_overlap")
    @classmethod
    def overlap_less_than_chunk(cls, v: int, info) -> int:
        """Overlap must be less than chunk size — otherwise we loop forever."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})"
            )
        return v
    
    @field_validator("gemini_api_key", "groq_api_key", "hf_api_key", mode="before")
    @classmethod
    def empty_string_as_empty(cls, v: str) -> str:
        """Treat placeholder values as empty strings."""
        placeholders = {
            "your_gemini_api_key_here",
            "your_groq_api_key_here", 
            "your_huggingface_token_here",
            "your_qdrant_api_key_here",
        }
        if v in placeholders:
            return ""
        return v
    
    def validate_for_startup(self) -> list[str]:
        """
        Check that required settings are present.
        Returns list of error messages (empty = all good).
        Called during app startup to fail fast with clear errors.
        """
        errors = []
        
        # LLM key check
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            errors.append(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini. "
                "Get it at: https://aistudio.google.com/"
            )
        if self.llm_provider == "groq" and not self.groq_api_key:
            errors.append(
                "GROQ_API_KEY is required when LLM_PROVIDER=groq. "
                "Get it at: https://console.groq.com/"
            )
        
        # Embedding key check (only for cloud provider)
        if self.embedding_provider == "huggingface" and not self.hf_api_key:
            errors.append(
                "HF_API_KEY is required when EMBEDDING_PROVIDER=huggingface. "
                "Get it at: https://huggingface.co/settings/tokens"
            )
        
        # Qdrant key check
        if self.vector_db_provider == "qdrant":
            if not self.qdrant_url:
                errors.append("QDRANT_URL is required when VECTOR_DB_PROVIDER=qdrant")
            if not self.qdrant_api_key:
                errors.append("QDRANT_API_KEY is required when VECTOR_DB_PROVIDER=qdrant")
        
        return errors


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    
    Why lru_cache?
    - Settings are read from disk/env on first call
    - Subsequent calls return the cached instance (fast)
    - In tests, you can clear the cache to reload settings
    - Use: get_settings.cache_clear() in test setup
    
    FastAPI dependency injection calls this function on every
    request — caching ensures we don't re-read .env thousands
    of times per second.
    """
    return Settings()