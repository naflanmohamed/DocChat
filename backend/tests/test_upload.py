"""
Tests for Upload API Endpoint
==============================
POST /api/upload
GET  /api/documents
GET  /api/documents/{id}
"""

import io
import pytest
from fastapi.testclient import TestClient


class TestUploadEndpoint:

    def test_upload_txt_file_returns_200(self, test_client):
        file_content = b"This is a test document with enough content for chunking. " * 20
        response = test_client.post(
            "/api/upload",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            data={"user_id": "test_user"},
        )
        assert response.status_code == 200

    def test_upload_returns_document_id(self, test_client):
        file_content = b"Test document content. " * 20
        response = test_client.post(
            "/api/upload",
            files={"file": ("report.txt", io.BytesIO(file_content), "text/plain")},
            data={"user_id": "test_user"},
        )
        data = response.json()
        assert "document_id" in data
        assert len(data["document_id"]) > 0

    def test_upload_returns_processing_status(self, test_client):
        file_content = b"Test content. " * 20
        response = test_client.post(
            "/api/upload",
            files={"file": ("doc.txt", io.BytesIO(file_content), "text/plain")},
            data={"user_id": "test_user"},
        )
        data = response.json()
        assert data["status"] == "processing"

    def test_upload_wrong_extension_rejected(self, test_client):
        response = test_client.post(
            "/api/upload",
            files={"file": ("malware.exe", io.BytesIO(b"bad file"), "application/octet-stream")},
            data={"user_id": "test_user"},
        )
        assert response.status_code == 400

    def test_upload_empty_file_rejected(self, test_client):
        response = test_client.post(
            "/api/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
            data={"user_id": "test_user"},
        )
        assert response.status_code == 400

    def test_upload_no_file_rejected(self, test_client):
        response = test_client.post("/api/upload")
        assert response.status_code == 422

    def test_upload_returns_filename(self, test_client):
        file_content = b"Content here. " * 20
        response = test_client.post(
            "/api/upload",
            files={"file": ("myfile.txt", io.BytesIO(file_content), "text/plain")},
            data={"user_id": "test_user"},
        )
        data = response.json()
        assert data["filename"] == "myfile.txt"


class TestDocumentsEndpoint:

    def test_list_documents_returns_200(self, test_client):
        response = test_client.get("/api/documents?user_id=test_user")
        assert response.status_code == 200

    def test_list_documents_returns_list(self, test_client):
        response = test_client.get("/api/documents?user_id=test_user")
        data = response.json()
        assert "documents" in data
        assert "total_count" in data
        assert isinstance(data["documents"], list)

    def test_get_nonexistent_document_returns_404(self, test_client):
        response = test_client.get("/api/documents/nonexistent_id_xyz")
        assert response.status_code == 404

    def test_upload_then_status_check(self, test_client):
        """Upload a file then immediately check its status."""
        file_content = b"Status check test content. " * 20
        upload_response = test_client.post(
            "/api/upload",
            files={"file": ("status_test.txt", io.BytesIO(file_content), "text/plain")},
            data={"user_id": "status_test_user"},
        )
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["document_id"]

        status_response = test_client.get(f"/api/documents/{doc_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["document_id"] == doc_id
        assert status_data["status"] in ["processing", "ready", "error"]