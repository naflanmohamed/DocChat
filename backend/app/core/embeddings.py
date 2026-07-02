"""
Embedding Service
=================
Converts text into vectors using sentence-transformers.

Design pattern: Provider abstraction
- BaseEmbedder defines the interface
- LocalEmbedder runs the model on your machine (no API needed)
- HuggingFaceEmbedder calls the HF Inference API (cloud, free tier)
- get_embedder() factory returns the right one based on config

This means the rest of the code only knows about BaseEmbedder.
Switching providers = change one env variable.

Performance notes:
- Local: ~50ms per batch on CPU, instant after first load
- HF API: ~200-500ms per batch (network round trip)
- Both support batching: embed 100 chunks in one call
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract base class all embedding providers must implement."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts.
        Returns a list of vectors, one per input text.
        All vectors have the same number of dimensions.
        """
        ...

    def embed_text(self, text: str) -> list[float]:
        """Convenience method to embed a single text."""
        return self.embed_texts([text])[0]

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Number of dimensions in the output vectors."""
        ...


class LocalEmbedder(BaseEmbedder):
    """
    Runs the embedding model locally using sentence-transformers.

    Advantages:
    - No API key required
    - No rate limits
    - Works offline
    - Free forever

    Disadvantages:
    - ~90MB model download on first run (cached after)
    - Uses CPU by default (slow on large batches without GPU)
    - Takes ~2 seconds to load the model on first use

    The model is loaded once and cached in memory.
    Subsequent calls reuse the loaded model (fast).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None  # Lazy loading — don't load until first use
        logger.info(f"LocalEmbedder configured with model: {model_name}")

    def _get_model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            logger.info(
                f"Loading embedding model '{self.model_name}' "
                "(first load may take ~10 seconds)..."
            )
            start = time.time()
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            elapsed = time.time() - start
            logger.info(f"Model loaded in {elapsed:.1f}s")
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts locally.

        Batching is important: embedding 100 texts in one call
        is much faster than 100 individual calls, because the
        model processes them in parallel on the GPU/CPU.
        """
        if not texts:
            return []

        model = self._get_model()

        # SentenceTransformer handles batching internally
        # show_progress_bar=False keeps logs clean
        embeddings = model.encode(
            texts,
            convert_to_tensor=False,  # Return numpy arrays
            show_progress_bar=False,
            batch_size=32,            # Process 32 texts at a time
        )

        # Convert numpy arrays to Python lists (JSON-serializable)
        return [emb.tolist() for emb in embeddings]

    @property
    def dimensions(self) -> int:
        return 384  # all-MiniLM-L6-v2 output size


class HuggingFaceEmbedder(BaseEmbedder):
    """
    Calls the HuggingFace Inference API for embeddings.

    Free tier limits:
    - ~30,000 requests/day
    - Rate limited (~10 req/sec)

    The API returns embeddings immediately if the model is warm.
    If cold (not recently used), it may take 20-30 seconds to load.
    We handle this with wait_for_model=True.
    """

    HF_API_BASE = "https://api-inference.huggingface.co/pipeline/feature-extraction"

    def __init__(self, api_key: str, model_name: str = "all-MiniLM-L6-v2"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = f"{self.HF_API_BASE}/{model_name}"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        logger.info(f"HuggingFaceEmbedder configured: {model_name}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed texts using HF Inference API.
        Processes in batches of 20 to stay within rate limits.
        """
        if not texts:
            return []

        all_embeddings = []

        # Process in batches of 20 (HF API limit)
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches for rate limiting
            if i + batch_size < len(texts):
                time.sleep(0.1)

        return all_embeddings

    def _embed_batch(self, texts: list[str], retry: int = 3) -> list[list[float]]:
        """Embed one batch with retry logic."""
        for attempt in range(retry):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "inputs": texts,
                        "options": {
                            "wait_for_model": True,
                            "use_cache": True,
                        },
                    },
                    timeout=60,  # Model loading can take up to 60s
                )

                if response.status_code == 503:
                    # Model is loading — wait and retry
                    wait_time = 20 * (attempt + 1)
                    logger.warning(
                        f"HF model loading, waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{retry})"
                    )
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                result = response.json()

                # HF returns list of embeddings for batch input
                if isinstance(result[0], list) and isinstance(result[0][0], float):
                    return result  # Already in correct format
                else:
                    # Sometimes returns nested lists — flatten one level
                    return [emb if isinstance(emb[0], float) else emb[0]
                            for emb in result]

            except requests.RequestException as e:
                if attempt == retry - 1:
                    raise RuntimeError(
                        f"HuggingFace API failed after {retry} attempts: {e}"
                    )
                time.sleep(5)

        raise RuntimeError("Failed to get embeddings from HuggingFace API")

    @property
    def dimensions(self) -> int:
        return 384


def get_embedder(
    provider: str = "local",
    model_name: str = "all-MiniLM-L6-v2",
    hf_api_key: str = "",
) -> BaseEmbedder:
    """
    Factory function — returns the configured embedder.

    Called once at startup, the embedder is stored and reused.
    This avoids reloading the model on every request.
    """
    if provider == "local":
        return LocalEmbedder(model_name=model_name)
    elif provider == "huggingface":
        if not hf_api_key:
            raise ValueError(
                "HF_API_KEY is required when EMBEDDING_PROVIDER=huggingface"
            )
        return HuggingFaceEmbedder(api_key=hf_api_key, model_name=model_name)
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            "Use 'local' or 'huggingface'"
        )