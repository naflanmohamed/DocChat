"""
Tests for Health Check Endpoint
=================================
GET /api/health
"""


class TestHealthEndpoint:

    def test_health_returns_200(self, test_client):
        response = test_client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_status(self, test_client):
        response = test_client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_returns_version(self, test_client):
        response = test_client.get("/api/health")
        data = response.json()
        assert "version" in data

    def test_health_returns_services(self, test_client):
        response = test_client.get("/api/health")
        data = response.json()
        assert "services" in data
        assert isinstance(data["services"], dict)

    def test_health_returns_uptime(self, test_client):
        response = test_client.get("/api/health")
        data = response.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_root_endpoint_returns_200(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_returns_name(self, test_client):
        response = test_client.get("/")
        data = response.json()
        assert "name" in data
        assert "status" in data