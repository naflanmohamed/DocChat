"""
Tests for Chat API Endpoint
=============================
POST /api/chat
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestChatEndpoint:

    def test_chat_returns_200_with_mocked_rag(self, test_client):
        """Chat endpoint returns 200 when RAG pipeline is mocked."""
        mock_response = MagicMock()
        mock_response.answer = "The Q3 revenue was $4.2 million [Source 1]."
        mock_response.citations = []
        mock_response.all_retrieved = []
        mock_response.model_used = "groq/llama-3.3-70b-versatile"
        mock_response.has_relevant_sources = True

        with patch("app.api.chat.RAGChain") as MockRAGChain:
            MockRAGChain.return_value.query.return_value = mock_response
            with patch("app.api.chat.get_embedder"):
                with patch("app.api.chat.get_vector_store"):
                    response = test_client.post(
                        "/api/chat",
                        json={
                            "question": "What was Q3 revenue?",
                            "session_id": "test-session-123",
                            "user_id": "test_user",
                            "conversation_history": [],
                        },
                    )
        assert response.status_code == 200

    def test_chat_response_has_required_fields(self, test_client):
        """Response must contain answer, citations, session_id."""
        mock_response = MagicMock()
        mock_response.answer = "Test answer [Source 1]."
        mock_response.citations = []
        mock_response.all_retrieved = []
        mock_response.model_used = "groq/llama-3.3-70b-versatile"
        mock_response.has_relevant_sources = False

        with patch("app.api.chat.RAGChain") as MockRAGChain:
            MockRAGChain.return_value.query.return_value = mock_response
            with patch("app.api.chat.get_embedder"):
                with patch("app.api.chat.get_vector_store"):
                    response = test_client.post(
                        "/api/chat",
                        json={
                            "question": "Test question?",
                            "session_id": "session-abc",
                            "user_id": "test_user",
                            "conversation_history": [],
                        },
                    )
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "session_id" in data
        assert data["session_id"] == "session-abc"

    def test_chat_empty_question_rejected(self, test_client):
        response = test_client.post(
            "/api/chat",
            json={
                "question": "",
                "session_id": "test-session",
                "user_id": "test_user",
                "conversation_history": [],
            },
        )
        assert response.status_code == 422

    def test_chat_missing_question_rejected(self, test_client):
        response = test_client.post(
            "/api/chat",
            json={
                "session_id": "test-session",
                "user_id": "test_user",
            },
        )
        assert response.status_code == 422

    def test_chat_with_conversation_history(self, test_client):
        mock_response = MagicMock()
        mock_response.answer = "Following up on the previous answer [Source 1]."
        mock_response.citations = []
        mock_response.all_retrieved = []
        mock_response.model_used = "groq/llama-3.3-70b-versatile"
        mock_response.has_relevant_sources = True

        with patch("app.api.chat.RAGChain") as MockRAGChain:
            MockRAGChain.return_value.query.return_value = mock_response
            with patch("app.api.chat.get_embedder"):
                with patch("app.api.chat.get_vector_store"):
                    response = test_client.post(
                        "/api/chat",
                        json={
                            "question": "Tell me more.",
                            "session_id": "session-with-history",
                            "user_id": "test_user",
                            "conversation_history": [
                                {"role": "user", "content": "What was Q3 revenue?"},
                                {"role": "assistant", "content": "Q3 revenue was $4.2M."},
                            ],
                        },
                    )
        assert response.status_code == 200


class TestRAGChain:
    """Unit tests for the RAG chain logic directly."""

    def test_rag_chain_query_calls_embedder(self, mock_embedder, mock_vector_store):
        from app.core.rag_chain import RAGChain

        with patch.object(
            RAGChain, "_call_llm", return_value="Test answer [Source 1]."
        ):
            chain = RAGChain(
                embedder=mock_embedder,
                vector_store=mock_vector_store,
                llm_provider="groq",
                groq_api_key="test-key",
                groq_model="llama-3.3-70b-versatile",
            )
            response = chain.query(
                question="What was Q3 revenue?",
                user_id="test_user",
            )

        mock_embedder.embed_text.assert_called_once_with("What was Q3 revenue?")
        assert response.answer == "Test answer [Source 1]."

    def test_rag_chain_query_calls_vector_store(self, mock_embedder, mock_vector_store):
        from app.core.rag_chain import RAGChain

        with patch.object(
            RAGChain, "_call_llm", return_value="Answer [Source 1]."
        ):
            chain = RAGChain(
                embedder=mock_embedder,
                vector_store=mock_vector_store,
                llm_provider="groq",
                groq_api_key="test-key",
                groq_model="llama-3.3-70b-versatile",
            )
            chain.query(question="Test?", user_id="user1")

        mock_vector_store.search.assert_called_once()

    def test_extract_citation_indices(self):
        from app.core.rag_chain import RAGChain

        chain = RAGChain.__new__(RAGChain)
        answer = "Revenue was $4.2M [Source 1]. Margin fell [Source 2][Source 1]."
        indices = chain._extract_citation_indices(answer)
        assert indices == [1, 2]

    def test_extract_citation_indices_no_citations(self):
        from app.core.rag_chain import RAGChain

        chain = RAGChain.__new__(RAGChain)
        answer = "I cannot find this information in the provided documents."
        indices = chain._extract_citation_indices(answer)
        assert indices == []

    def test_no_relevant_sources_still_returns_answer(
        self, mock_embedder, mock_vector_store
    ):
        from app.core.rag_chain import RAGChain

        mock_vector_store.search.return_value = []

        with patch.object(
            RAGChain, "_call_llm",
            return_value="I cannot find this information in the provided documents."
        ):
            chain = RAGChain(
                embedder=mock_embedder,
                vector_store=mock_vector_store,
                llm_provider="groq",
                groq_api_key="test-key",
                groq_model="llama-3.3-70b-versatile",
            )
            response = chain.query(question="Unknown topic?", user_id="user1")

        assert response.has_relevant_sources is False
        assert "cannot find" in response.answer.lower()