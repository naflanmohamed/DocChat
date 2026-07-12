"""
Test Configuration and Fixtures
================================
Fixtures are shared test helpers. Define once, use in any test file.
pytest automatically injects them by parameter name.
"""

import os
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


# Set test environment variables BEFORE importing the app
os.environ["ENVIRONMENT"] = "development"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["LLM_PROVIDER"] = "groq"
os.environ["GROQ_MODEL"] = "llama-3.3-70b-versatile"
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EMBEDDING_MODEL"] = "all-MiniLM-L6-v2"
os.environ["VECTOR_DB_PROVIDER"] = "chroma"
os.environ["UPLOAD_DIR"] = "./test_uploads"
os.environ["CHROMA_PERSIST_DIR"] = "./test_chroma_db"


@pytest.fixture(scope="session")
def test_client():
    """
    Create a FastAPI test client.
    scope="session" means one client for the entire test session (faster).
    """
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def sample_txt_file():
    """Create a temporary TXT file for upload tests."""
    content = """
    TechCorp Annual Report 2024

    Q3 Financial Results:
    Revenue reached $4.2 million in Q3, representing a 23% year-over-year increase.
    This exceeded analyst expectations by 12%.

    Q3 Challenges:
    Supply chain disruptions reduced gross margin from 68% to 61%.
    Operations team estimates recovery by Q1 2025.

    Team Growth:
    Headcount grew from 142 to 189 employees in 2024.
    New offices opened in Singapore and Toronto.
    """

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8"
    ) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup after all tests
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_embedder():
    """Mock embedder that returns fake vectors without loading the real model."""
    embedder = MagicMock()
    # Return a 384-dimensional zero vector (matches all-MiniLM-L6-v2)
    embedder.embed_text.return_value = [0.1] * 384
    embedder.embed_texts.return_value = [[0.1] * 384, [0.2] * 384]
    embedder.dimensions = 384
    return embedder


@pytest.fixture
def mock_vector_store():
    """Mock vector store that doesn't require a real Chroma DB."""
    from app.vectordb.base import SearchResult

    store = MagicMock()
    store.upsert_chunks.return_value = 5
    store.health_check.return_value = True
    store.search.return_value = [
        SearchResult(
            chunk_id="test_chunk_0",
            text="Revenue reached $4.2 million in Q3.",
            score=0.92,
            document_id="test_doc_123",
            document_name="annual_report.txt",
            page_number=1,
            chunk_index=0,
            user_id="test_user",
        ),
        SearchResult(
            chunk_id="test_chunk_1",
            text="This exceeded analyst expectations by 12%.",
            score=0.85,
            document_id="test_doc_123",
            document_name="annual_report.txt",
            page_number=1,
            chunk_index=1,
            user_id="test_user",
        ),
    ]
    return store


@pytest.fixture(autouse=True)
def cleanup_test_dirs():
    """Clean up test directories before and after each test."""
    import shutil
    dirs = ["./test_uploads", "./test_chroma_db"]

    for d in dirs:
        os.makedirs(d, exist_ok=True)

    yield

    # Don't delete between tests — only at session end
    # This lets integration tests share uploaded files