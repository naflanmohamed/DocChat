"""
Text Chunker
============
Splits extracted document text into overlapping chunks
suitable for embedding and retrieval.

Why LangChain's RecursiveCharacterTextSplitter?
- Respects natural language boundaries (paragraphs → sentences → words)
- Configurable chunk size and overlap
- Adds metadata to every chunk automatically
- Battle-tested in production RAG systems

The metadata attached to each chunk is what powers citations.
Without it, we'd have the text but not know where it came from.
"""

import logging
from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document as LangChainDocument

from app.core.document_processor import ExtractedDocument

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """
    A single chunk ready for embedding and storage.

    chunk_id:      Unique ID used as the vector DB record ID
    text:          The actual text content to embed
    document_id:   Which document this came from
    document_name: Original filename (shown in citations)
    page_number:   Page in the source document
    chunk_index:   Position of this chunk within the document
    total_chunks:  Total chunks in this document
    user_id:       Owner of the document (for namespace isolation)
    """
    chunk_id: str
    text: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    total_chunks: int
    user_id: str

    @property
    def metadata(self) -> dict:
        """Return metadata dict for vector DB storage."""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "user_id": self.user_id,
        }


class DocumentChunker:
    """
    Converts an ExtractedDocument into a list of DocumentChunks.

    Usage:
        chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
        chunks = chunker.chunk(extracted_doc, document_id="abc123", user_id="user1")
        print(len(chunks))  # e.g. 47 chunks
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # RecursiveCharacterTextSplitter splits in this priority order:
        # 1. Double newlines (paragraph boundaries)
        # 2. Single newlines (line boundaries)
        # 3. Sentences ending with ". "
        # 4. Words (spaces)
        # 5. Individual characters (last resort)
        # This ensures splits happen at natural language boundaries
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
            is_separator_regex=False,
        )

    def chunk(
        self,
        extracted_doc: ExtractedDocument,
        document_id: str,
        user_id: str,
    ) -> list[DocumentChunk]:
        """
        Split an extracted document into chunks.

        Strategy: chunk page-by-page, preserving page number in metadata.
        This means a chunk never spans two pages — accurate citations.

        Alternative strategy: chunk the full document as one string.
        Simpler but loses page boundary information.
        We use page-by-page for citation accuracy.
        """
        if extracted_doc.is_empty:
            logger.warning(
                f"Document {extracted_doc.filename} is empty, "
                "no chunks produced"
            )
            return []

        all_chunks: list[DocumentChunk] = []
        chunk_index = 0  # Global chunk index across all pages

        for page in extracted_doc.pages:
            if not page.text.strip():
                continue

            # Split this page's text into chunks
            page_texts = self.splitter.split_text(page.text)

            for page_chunk_text in page_texts:
                cleaned = page_chunk_text.strip()
                if not cleaned:
                    continue

                # Minimum chunk size filter
                # Very short chunks (< 50 chars) are usually noise
                # like page numbers, headers, etc.
                if len(cleaned) < 50:
                    logger.debug(f"Skipping short chunk: '{cleaned[:30]}...'")
                    continue

                chunk = DocumentChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    text=cleaned,
                    document_id=document_id,
                    document_name=extracted_doc.filename,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be updated below
                    user_id=user_id,
                )
                all_chunks.append(chunk)
                chunk_index += 1

        # Update total_chunks now that we know the final count
        total = len(all_chunks)
        for chunk in all_chunks:
            chunk.total_chunks = total

        logger.info(
            f"Chunked {extracted_doc.filename}: "
            f"{extracted_doc.total_pages} pages → {total} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

        return all_chunks