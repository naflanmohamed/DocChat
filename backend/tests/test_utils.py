"""
Tests for Utility Functions
============================
"""

import pytest
from app.utils.file_utils import (
    generate_document_id,
    get_file_extension,
    is_allowed_extension,
    safe_filename,
    format_file_size,
)
from app.utils.text_utils import (
    clean_text,
    estimate_token_count,
    truncate_text,
    extract_citations_from_answer,
)


class TestFileUtils:

    def test_generate_document_id_is_deterministic(self):
        id1 = generate_document_id("report.pdf", "user1")
        id2 = generate_document_id("report.pdf", "user1")
        assert id1 == id2

    def test_different_users_get_different_ids(self):
        id1 = generate_document_id("report.pdf", "user1")
        id2 = generate_document_id("report.pdf", "user2")
        assert id1 != id2

    def test_different_files_get_different_ids(self):
        id1 = generate_document_id("file1.pdf", "user1")
        id2 = generate_document_id("file2.pdf", "user1")
        assert id1 != id2

    def test_get_file_extension_pdf(self):
        assert get_file_extension("report.PDF") == "pdf"

    def test_get_file_extension_docx(self):
        assert get_file_extension("document.DOCX") == "docx"

    def test_get_file_extension_normalizes_case(self):
        assert get_file_extension("FILE.TXT") == "txt"

    def test_is_allowed_extension_valid(self):
        assert is_allowed_extension("report.pdf", ["pdf", "docx", "txt"]) is True

    def test_is_allowed_extension_invalid(self):
        assert is_allowed_extension("virus.exe", ["pdf", "docx", "txt"]) is False

    def test_safe_filename_removes_path_traversal(self):
        result = safe_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_safe_filename_handles_spaces(self):
        result = safe_filename("my report.pdf")
        assert " " not in result

    def test_format_file_size_bytes(self):
        assert "B" in format_file_size(500)

    def test_format_file_size_kb(self):
        assert "KB" in format_file_size(2048)

    def test_format_file_size_mb(self):
        assert "MB" in format_file_size(5 * 1024 * 1024)


class TestTextUtils:

    def test_clean_text_removes_multiple_spaces(self):
        result = clean_text("Hello   world")
        assert "   " not in result

    def test_clean_text_normalizes_newlines(self):
        result = clean_text("Line 1\n\n\n\nLine 2")
        assert "\n\n\n" not in result

    def test_clean_text_empty_string(self):
        result = clean_text("")
        assert result == ""

    def test_estimate_token_count(self):
        text = "a" * 400  # 400 chars → ~100 tokens
        count = estimate_token_count(text)
        assert count == 100

    def test_truncate_text_short_text_unchanged(self):
        text = "Hello world"
        result = truncate_text(text, 100)
        assert result == text

    def test_truncate_text_long_text_truncated(self):
        text = "A" * 200
        result = truncate_text(text, 50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_extract_citations_from_answer(self):
        answer = "Revenue was $4.2M [Source 1]. Margin fell [Source 2]."
        citations = extract_citations_from_answer(answer)
        assert citations == [1, 2]

    def test_extract_citations_deduplicates(self):
        answer = "See [Source 1] and also [Source 1] again."
        citations = extract_citations_from_answer(answer)
        assert citations == [1]

    def test_extract_citations_empty_answer(self):
        citations = extract_citations_from_answer("")
        assert citations == []

    def test_extract_citations_no_citations(self):
        citations = extract_citations_from_answer("No sources cited here.")
        assert citations == []