"""
RAG Chain
=========
Orchestrates the complete Retrieval-Augmented Generation pipeline.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests

from app.core.embeddings import BaseEmbedder
from app.vectordb.base import VectorDBBase, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    answer: str
    citations: list[SearchResult]
    all_retrieved: list[SearchResult]
    model_used: str
    has_relevant_sources: bool


class RAGChain:

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: VectorDBBase,
        llm_provider: str = "gemini",
        gemini_api_key: str = "",
        gemini_model: str = "gemini-2.0-flash",
        groq_api_key: str = "",
        groq_model: str = "llama-3.3-70b-versatile",
        max_retrieval_docs: int = 5,
        min_relevance_score: float = 0.3,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.groq_api_key = groq_api_key
        self.groq_model = groq_model
        self.max_retrieval_docs = max_retrieval_docs
        self.min_relevance_score = min_relevance_score

    def query(
        self,
        question: str,
        user_id: str,
        conversation_history: Optional[list[dict]] = None,
        document_ids: Optional[list[str]] = None,
    ) -> RAGResponse:
        conversation_history = conversation_history or []

        logger.info(f"RAG query: '{question[:80]}' for user '{user_id}'")

        query_embedding = self.embedder.embed_text(question)

        retrieved = self.vector_store.search(
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=self.max_retrieval_docs,
            document_ids=document_ids,
        )

        relevant = [r for r in retrieved if r.score >= self.min_relevance_score]
        has_relevant = len(relevant) > 0

        if not has_relevant:
            best = f"{retrieved[0].score:.3f}" if retrieved else "N/A"
            logger.warning(
                f"No relevant chunks found (threshold={self.min_relevance_score}). "
                f"Best score: {best}"
            )

        messages = self._build_prompt(
            question=question,
            retrieved_chunks=relevant if has_relevant else retrieved[:2],
            conversation_history=conversation_history,
            has_relevant=has_relevant,
        )

        answer = self._call_llm(messages)

        cited_indices = self._extract_citation_indices(answer)
        source_list = relevant if has_relevant else retrieved[:2]
        cited_chunks = [
            source_list[i - 1]
            for i in cited_indices
            if 1 <= i <= len(source_list)
        ]

        logger.info(
            f"RAG complete: {len(relevant)} relevant chunks, "
            f"{len(cited_chunks)} cited, "
            f"answer length: {len(answer)} chars"
        )

        return RAGResponse(
            answer=answer,
            citations=cited_chunks,
            all_retrieved=retrieved,
            model_used=(
                f"{self.llm_provider}/"
                f"{self.gemini_model if self.llm_provider == 'gemini' else self.groq_model}"
            ),
            has_relevant_sources=has_relevant,
        )

    def _build_prompt(
        self,
        question: str,
        retrieved_chunks: list[SearchResult],
        conversation_history: list[dict],
        has_relevant: bool,
    ) -> list[dict]:
        system_prompt = """You are a precise document analyst. Your job is to answer questions based ONLY on the provided source documents.

STRICT RULES:
1. Base your answer ONLY on the provided sources below
2. After every factual claim, add a citation like [Source 1] or [Source 2]
3. If multiple sources support a claim, cite all of them: [Source 1][Source 3]
4. If the answer is not found in the sources, respond with:
   "I cannot find this information in the provided documents."
5. Never use your general training knowledge to fill gaps
6. If sources partially answer the question, answer what you can and explicitly note what is missing
7. Be concise, accurate, and cite every claim"""

        if retrieved_chunks:
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks, 1):
                context_parts.append(
                    f"[Source {i}] {chunk.document_name} "
                    f"(Page {chunk.page_number}, "
                    f"Relevance: {chunk.score:.2f}):\n"
                    f"{chunk.text}"
                )
            context = "\n\n---\n\n".join(context_parts)
            context_block = f"DOCUMENT SOURCES:\n\n{context}"
        else:
            context_block = (
                "DOCUMENT SOURCES: No documents have been uploaded yet. "
                "Please ask the user to upload documents first."
            )

        messages = [{"role": "system", "content": system_prompt}]

        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({
            "role": "user",
            "content": f"{context_block}\n\nQUESTION: {question}",
        })

        return messages

    def _call_llm(self, messages: list[dict]) -> str:
        """Route to LLM provider with automatic fallback."""
        if self.llm_provider == "gemini":
            try:
                return self._call_gemini(messages)
            except RuntimeError as e:
                if "429" in str(e) and self.groq_api_key:
                    logger.warning("Gemini quota exceeded, falling back to Groq")
                    return self._call_groq(messages)
                raise
        elif self.llm_provider == "groq":
            return self._call_groq(messages)
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

    def _call_gemini(self, messages: list[dict]) -> str:
        """Call Google Gemini API."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
            f"?key={self.gemini_api_key}"
        )

        system_text = ""
        conversation_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                conversation_messages.append(msg)

        contents = []
        for i, msg in enumerate(conversation_messages):
            if msg["role"] == "user":
                text = msg["content"]
                if i == 0 and system_text:
                    text = f"{system_text}\n\n---\n\n{text}"
                contents.append({
                    "role": "user",
                    "parts": [{"text": text}]
                })
            elif msg["role"] == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 2048,
                "topP": 0.95,
            },
        }

        response = requests.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.status_code} {response.text}")
            raise RuntimeError(
                f"Gemini API returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Gemini response format: {data}")
            raise RuntimeError(f"Failed to parse Gemini response: {e}")

    def _call_groq(self, messages: list[dict]) -> str:
        """Call Groq API (OpenAI-compatible format)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 2048,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            logger.error(f"Groq API error: {response.status_code} {response.text}")
            raise RuntimeError(
                f"Groq API returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def stream_query(
        self,
        question: str,
        user_id: str,
        conversation_history: list[dict] | None = None,
        document_ids: list[str] | None = None,
    ):
        """
        Stream the RAG response token by token.
        Yields strings — each string is a chunk of the answer.

        Usage:
            for chunk in chain.stream_query(...):
                print(chunk, end="", flush=True)
        """
        conversation_history = conversation_history or []

        logger.info(f"Streaming RAG query: '{question[:60]}' for user '{user_id}'")

        # Steps 1-4 are identical to query() — embed, search, filter, build prompt
        query_embedding = self.embedder.embed_text(question)

        retrieved = self.vector_store.search(
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=self.max_retrieval_docs,
            document_ids=document_ids,
        )

        relevant = [r for r in retrieved if r.score >= self.min_relevance_score]
        has_relevant = len(relevant) > 0

        messages = self._build_prompt(
            question=question,
            retrieved_chunks=relevant if has_relevant else retrieved[:2],
            conversation_history=conversation_history,
            has_relevant=has_relevant,
        )

        # Yield retrieved sources first as metadata
        # Frontend uses this to render citation cards immediately
        import json
        sources = relevant if has_relevant else retrieved[:2]
        source_data = [
            {
                "chunk_id": s.chunk_id,
                "document_name": s.document_name,
                "page_number": s.page_number,
                "score": s.score,
                "excerpt": s.text[:200],
            }
            for s in sources
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': source_data})}\n\n"

        # Stream the LLM response
        if self.llm_provider == "gemini":
            yield from self._stream_gemini(messages)
        elif self.llm_provider == "groq":
            yield from self._stream_groq(messages)

        # Signal completion
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    def _stream_gemini(self, messages: list[dict]):
        """Stream from Gemini using server-sent events."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:streamGenerateContent"
            f"?key={self.gemini_api_key}&alt=sse"
        )

        system_text = ""
        conversation_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                conversation_messages.append(msg)

        contents = []
        for i, msg in enumerate(conversation_messages):
            if msg["role"] == "user":
                text = msg["content"]
                if i == 0 and system_text:
                    text = f"{system_text}\n\n---\n\n{text}"
                contents.append({"role": "user", "parts": [{"text": text}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 2048,
            },
        }

        import json
        with requests.post(url, json=payload, stream=True, timeout=60) as response:
            if response.status_code != 200:
                error_msg = f"Gemini streaming error: {response.status_code}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return

            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[6:])
                            text = (
                                data.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [{}])[0]
                                .get("text", "")
                            )
                            if text:
                                yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue

    def _stream_groq(self, messages: list[dict]):
        """Stream from Groq API using OpenAI-compatible streaming."""
        import json

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 2048,
            "stream": True,  # Enable streaming
        }

        with requests.post(
            url, headers=headers, json=payload, stream=True, timeout=60
        ) as response:
            if response.status_code != 200:
                error_msg = f"Groq streaming error: {response.status_code}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return

            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    def _extract_citation_indices(self, answer: str) -> list[int]:
        """Parse [Source N] citation markers from the LLM answer."""
        pattern = r"\[Source (\d+)\]"
        matches = re.findall(pattern, answer)

        seen = set()
        result = []
        for m in matches:
            n = int(m)
            if n not in seen:
                seen.add(n)
                result.append(n)

        return result