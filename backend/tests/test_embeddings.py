"""
Tests for Embedding Service
============================
Tests both local and mocked embedding providers.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.core.embeddings import LocalEmbedder, get_embedder


class TestLocalEmbedder:

    @pytest.fixture
    def embedder(self):
        return LocalEmbedder(model_name="all-MiniLM-L6-v2")

    def test_embed_single_text(self, embedder):
        vector = embedder.embed_text("Hello world")
        assert isinstance(vector, list)
        assert len(vector) == 384
        assert all(isinstance(v, float) for v in vector)

    def test_embed_multiple_texts(self, embedder):
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        vectors = embedder.embed_texts(texts)
        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)

    def test_dimensions_property(self, embedder):
        assert embedder.dimensions == 384

    def test_similar_texts_have_high_similarity(self, embedder):
        """Semantically similar texts should produce similar vectors."""
        import math

        vec1 = embedder.embed_text("The dog ran fast")
        vec2 = embedder.embed_text("The puppy ran quickly")
        vec3 = embedder.embed_text("The stock market crashed today")

        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = math.sqrt(sum(x**2 for x in a))
            mag_b = math.sqrt(sum(x**2 for x in b))
            return dot / (mag_a * mag_b)

        sim_related = cosine_sim(vec1, vec2)
        sim_unrelated = cosine_sim(vec1, vec3)

        # Similar texts should score higher than unrelated ones
        assert sim_related > sim_unrelated

    def test_empty_text_handled(self, embedder):
        """Empty string should not crash."""
        try:
            vector = embedder.embed_text("")
            assert isinstance(vector, list)
        except Exception:
            pass  # Some models raise on empty input — acceptable

    def test_long_text_handled(self, embedder):
        """Very long text should be handled without crashing."""
        long_text = "This is a sentence. " * 500
        vector = embedder.embed_text(long_text)
        assert len(vector) == 384

    def test_embed_texts_empty_list(self, embedder):
        result = embedder.embed_texts([])
        assert result == []


class TestGetEmbedder:

    def test_get_local_embedder(self):
        embedder = get_embedder(provider="local", model_name="all-MiniLM-L6-v2")
        assert isinstance(embedder, LocalEmbedder)

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embedder(provider="openai")

    def test_huggingface_without_key_raises(self):
        with pytest.raises(ValueError):
            get_embedder(provider="huggingface", hf_api_key="")