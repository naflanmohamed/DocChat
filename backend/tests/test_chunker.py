"""
Tests for Document Chunker
===========================
Verifies text splitting, overlap, and metadata attachment.
"""

import pytest
from app.core.chunker import DocumentChunker, DocumentChunk
from app.core.document_processor import DocumentProcessor, ExtractedDocument, ExtractedPage


def make_extracted_doc(text: str, filename: str = "test.txt") -> ExtractedDocument:
    """Helper to create an ExtractedDocument from raw text."""
    page = ExtractedPage(page_number=1, text=text)
    return ExtractedDocument(
        filename=filename,
        file_type="txt",
        pages=[page],
        total_pages=1,
        total_chars=len(text),
    )


class TestDocumentChunker:

    @pytest.fixture
    def chunker(self):
        return DocumentChunker(chunk_size=200, chunk_overlap=50)

    def test_basic_chunking(self, chunker):
        doc = make_extracted_doc("A" * 500)
        chunks = chunker.chunk(doc, document_id="doc1", user_id="user1")
        assert len(chunks) > 1

    def test_chunk_has_required_metadata(self, chunker):
        doc = make_extracted_doc(
            "This is a test document with enough content to form a chunk. " * 10
        )
        chunks = chunker.chunk(doc, document_id="doc123", user_id="user456")
        assert len(chunks) > 0

        chunk = chunks[0]
        assert chunk.document_id == "doc123"
        assert chunk.user_id == "user456"
        assert chunk.document_name == "test.txt"
        assert chunk.page_number == 1
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == len(chunks)

    def test_chunk_ids_are_unique(self, chunker):
        doc = make_extracted_doc("Content. " * 100)
        chunks = chunker.chunk(doc, document_id="doc1", user_id="user1")
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_ids_contain_document_id(self, chunker):
        doc = make_extracted_doc("Content. " * 100)
        chunks = chunker.chunk(doc, document_id="mydoc", user_id="user1")
        assert all("mydoc" in c.chunk_id for c in chunks)

    def test_empty_document_returns_no_chunks(self, chunker):
        doc = make_extracted_doc("")
        chunks = chunker.chunk(doc, document_id="empty", user_id="user1")
        assert chunks == []

    def test_short_chunks_filtered_out(self, chunker):
        """Chunks shorter than 50 chars should be filtered."""
        doc = make_extracted_doc("Hi.")
        chunks = chunker.chunk(doc, document_id="short", user_id="user1")
        assert all(len(c.text) >= 50 for c in chunks)

    def test_multipage_document(self):
        chunker = DocumentChunker(chunk_size=300, chunk_overlap=50)
        pages = [
            ExtractedPage(page_number=1, text="Page one content. " * 20),
            ExtractedPage(page_number=2, text="Page two content. " * 20),
            ExtractedPage(page_number=3, text="Page three content. " * 20),
        ]
        doc = ExtractedDocument(
            filename="multi.txt",
            file_type="txt",
            pages=pages,
            total_pages=3,
            total_chars=sum(len(p.text) for p in pages),
        )
        chunks = chunker.chunk(doc, document_id="multi", user_id="user1")
        page_numbers = {c.page_number for c in chunks}
        assert len(page_numbers) > 1

    def test_chunk_metadata_property(self, chunker):
        doc = make_extracted_doc("Test content for metadata. " * 20)
        chunks = chunker.chunk(doc, document_id="doc1", user_id="user1")
        assert len(chunks) > 0
        meta = chunks[0].metadata
        assert "document_id" in meta
        assert "document_name" in meta
        assert "page_number" in meta
        assert "user_id" in meta