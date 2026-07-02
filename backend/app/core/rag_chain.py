"""
RAG Chain
=========
Orchestrates the complete Retrieval-Augmented Generation pipeline.

Flow:
1. Receive question + user_id
2. Embed the question (same model as documents)
3. Search vector DB for relevant chunks
4. Build prompt with retrieved context
5. Call LLM (Gemini or Groq)
6. Parse response + map citations to metadata
7. Return structured answer with citations

This file is the most important in the backend.
Understanding it means understanding RAG.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, Generator

import requests

from app.core.embeddings import BaseEmbedder
from app.vectordb.base import VectorDBBase, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    answer: str
    citations: list[SearchResult]      # Only cited sources
    all_retrieved: list[SearchResult]  # All retrieved sources
    model_used: str
    has_relevant_sources: bool


class RAGChain:
    """
    The complete RAG pipeline.

    Usage:
        chain = RAGChain(embedder=embedder, vector_store=store, settings=settings)
        response = chain.query(
            question="What was Q3 revenue?",
            user_id="user1",
            conversation_history=[...]
        )
        print(response.answer)
        print(response.citations)
    """

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: VectorDBBase,
        llm_provider: str = "gemini",
        gemini_api_key: str = "",
        gemini_model: str = "gemini-1.5-flash",
        groq_api_key: str = "",
        groq_model: str = "llama-3.1-70b-versatile",
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
        """
        Execute the full RAG pipeline for a question.

        Steps:
        1. Embed the question
        2. Search vector DB
        3. Filter by relevance score
        4. Build prompt
        5. Call LLM
        6. Parse citations
        7. Return response
        """
        conversation_history = conversation_history or []

        logger.info(f"RAG query: '{question[:80]}...' for user '{user_id}'")

        # ── Step 1: Embed the question ───────────────────────
        logger.debug("Embedding question...")
        query_embedding = self.embedder.embed_text(question)

        # ── Step 2: Search vector DB ─────────────────────────
        logger.debug(f"Searching vector DB (top_k={self.max_retrieval_docs})...")
        retrieved = self.vector_store.search(
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=self.max_retrieval_docs,
            document_ids=document_ids,
        )

        # ── Step 3: Filter by relevance score ────────────────
        # Chunks with very low scores are noise — exclude them
        relevant = [r for r in retrieved if r.score >= self.min_relevance_score]

        has_relevant = len(relevant) > 0

        if not has_relevant:
            logger.warning(
                f"No relevant chunks found (threshold={self.min_relevance_score}). "
                f"Best score: {retrieved[0].score:.3f if retrieved else 'N/A'}"
            )

        # ── Step 4: Build prompt ─────────────────────────────
        messages = self._build_prompt(
            question=question,
            retrieved_chunks=relevant if has_relevant else retrieved[:2],
            conversation_history=conversation_history,
            has_relevant=has_relevant,
        )

        # ── Step 5: Call LLM ─────────────────────────────────
        logger.debug(f"Calling LLM ({self.llm_provider})...")
        answer = self._call_llm(messages)

        # ── Step 6: Parse citations ──────────────────────────
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
            model_used=f"{self.llm_provider}/{self.gemini_model if self.llm_provider == 'gemini' else self.groq_model}",
            has_relevant_sources=has_relevant,
        )

    def _build_prompt(
        self,
        question: str,
        retrieved_chunks: list[SearchResult],
        conversation_history: list[dict],
        has_relevant: bool,
    ) -> list[dict]:
        """
        Assemble the complete prompt for the LLM.

        Structure:
        1. System prompt (role + rules)
        2. Retrieved context (numbered sources)
        3. Conversation history (last N turns)
        4. Current question
        """

        # ── System Prompt ─────────────────────────────────────
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

        # ── Context Assembly ──────────────────────────────────
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

        # ── Build Messages ────────────────────────────────────
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (for multi-turn memory)
        # Keep last 10 turns to avoid token limits
        recent_history = conversation_history[-10:]
        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add current question with context
        messages.append({
            "role": "user",
            "content": f"{context_block}\n\nQUESTION: {question}",
        })

        return messages

    def _call_llm(self, messages: list[dict]) -> str:
        """Route to the configured LLM provider."""
        if self.llm_provider == "gemini":
            return self._call_gemini(messages)
        elif self.llm_provider == "groq":
            return self._call_groq(messages)
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

    def _call_gemini(self, messages: list[dict]) -> str:
        """Call Google Gemini 1.5 Flash API."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
            f"?key={self.gemini_api_key}"
        )

        # Convert to Gemini format
        system_text = ""
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            elif msg["role"] == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.0,       # Deterministic for factual Q&A
                "maxOutputTokens": 2048,
                "topP": 0.95,
            },
        }

        if system_text:
            payload["systemInstruction"] = {
                "parts": [{"text": system_text}]
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

    def _extract_citation_indices(self, answer: str) -> list[int]:
        """
        Parse [Source N] citation markers from the LLM answer.

        Example:
            "Revenue was $4.2M [Source 1]. Margin fell [Source 2][Source 1]."
            → [1, 2]  (unique, in order of appearance)
        """
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