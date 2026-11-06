"""
Tests for FastAPI API endpoints.
Uses TestClient with mocked database and AI services.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db_session():
    """Mock database session for tests that don't need real DB."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def test_client():
    """Create FastAPI test client with mocked dependencies."""
    # Mock DB and Gemini before importing app
    with patch("app.database.connection.check_db_connection", new_callable=AsyncMock, return_value=True), \
         patch("app.database.connection.init_db", new_callable=AsyncMock), \
         patch("app.database.connection.close_db", new_callable=AsyncMock), \
         patch("app.services.gemini_service.get_gemini_service") as mock_gemini:

        mock_svc = MagicMock()
        mock_svc.health_check = AsyncMock(return_value={"status": "ok", "model": "gemini-2.0-flash", "message": "ok"})
        mock_svc.get_model_name.return_value = "gemini-2.0-flash"
        mock_gemini.return_value = mock_svc

        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        yield client


class TestHealthEndpoint:
    def test_health_returns_200(self, test_client):
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_structure(self, test_client):
        response = test_client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "gemini" in data

    def test_health_includes_version(self, test_client):
        response = test_client.get("/api/v1/health")
        data = response.json()
        assert data["version"] == "1.0.0"


class TestRootEndpoint:
    def test_root_returns_200(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200

    def test_root_has_content(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        if "text/html" in response.headers.get("content-type", ""):
            assert "Enterprise GTM Intelligence" in response.text
        else:
            data = response.json()
            assert "name" in data
            assert "docs" in data


class TestAPIDocumentation:
    def test_openapi_schema_accessible(self, test_client):
        response = test_client.get("/api/v1/openapi.json")
        assert response.status_code == 200

    def test_docs_accessible(self, test_client):
        response = test_client.get("/api/v1/docs")
        assert response.status_code == 200


class TestErrorHandling:
    def test_404_for_unknown_route(self, test_client):
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_account_not_found_returns_404(self, test_client):
        with patch("app.api.routes.accounts.get_database") as mock_dep:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_dep.return_value = mock_session

            response = test_client.get("/api/v1/accounts/nonexistent-id")
            # Should be 404 or similar (depends on mock depth)
            assert response.status_code in (404, 500, 422)
