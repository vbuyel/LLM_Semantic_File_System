"""
Integration tests for gateway_auth FastAPI endpoints.
Uses TestClient to test routing, proxy logic, and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("OAUTH_GOOGLE_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("OAUTH_GOOGLE_BASE_URL", "http://localhost")
    monkeypatch.setenv("AGENT_SERVER", "http://localhost:8001")
    monkeypatch.setenv("FILE_OPS_SERVER", "http://localhost:8002")
    monkeypatch.setenv("EVENT_DB_URL", "http://localhost:8003")
    monkeypatch.setenv("EVENT_DB_WS_URL", "ws://localhost:8003/ws/gateway")


@pytest.fixture
def client(mock_settings):
    with patch("src.gateway_auth.adapters.events_ws.relay_events_from_eventdb"):
        from src.gateway_auth.endpoints.main import app
        with TestClient(app) as c:
            yield c


class TestGatewayHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestGatewayAIAgent:
    def test_ai_agent_success(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"text": "AI response"}
            mock_post.return_value = mock_resp

            resp = client.post("/gateway/ai_agent", json={"text": "test query"})
            assert resp.status_code == 200
            assert resp.json()["text"] == "AI response"


class TestGatewayGetObjects:
    def test_get_objects_success(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "files": [{"path": "/f", "name": "f", "isDirectory": False}],
                "storage_type": "gcs"
            }
            mock_get.return_value = mock_resp

            resp = client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 200

    def test_get_objects_service_unavailable(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.ConnectionError()
            resp = client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 503

    def test_get_objects_timeout(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.Timeout()
            resp = client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 504


class TestGatewayDeleteObject:
    def test_delete_success(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.delete") as mock_del:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"message": "deleted"}
            mock_del.return_value = mock_resp

            resp = client.delete("/gateway/delete_object?path=test.txt")
            assert resp.status_code == 200

    def test_delete_service_unavailable(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.delete") as mock_del:
            import requests
            mock_del.side_effect = requests.exceptions.ConnectionError()
            resp = client.delete("/gateway/delete_object?path=test.txt")
            assert resp.status_code == 503


class TestGatewayRenameObject:
    def test_rename_success(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.put") as mock_put:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"message": "renamed"}
            mock_put.return_value = mock_resp

            resp = client.put("/gateway/rename_object?path=old.txt&new_name=new.txt")
            assert resp.status_code == 200


class TestGatewayDownloadObject:
    def test_download_success(self, client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"file content"
            mock_resp.headers = {
                "content-type": "application/octet-stream",
                "Content-Disposition": 'attachment; filename="test.txt"',
            }
            mock_get.return_value = mock_resp

            resp = client.get("/gateway/download_object?path=test.txt")
            assert resp.status_code == 200


class TestOAuthRouter:
    def test_google_url_redirects(self, client):
        with patch("src.gateway_auth.endpoints.oauth_router.generate_google_oauth_redirect_uri") as mock_gen:
            mock_gen.return_value = "https://accounts.google.com/o/oauth2/v2/auth?test=1"
            resp = client.get("/auth/google/url", follow_redirects=False)
            assert resp.status_code == 302


class TestEventsRouter:
    def test_get_user_events(self, client):
        from unittest.mock import AsyncMock

        mock_r = MagicMock()
        mock_r.json.return_value = {"events": []}
        mock_r.raise_for_status = MagicMock()

        mock_ac = AsyncMock()
        mock_ac.get = AsyncMock(return_value=mock_r)
        mock_ac.__aenter__.return_value = mock_ac

        with patch("src.gateway_auth.endpoints.events_router.httpx.AsyncClient", return_value=mock_ac):
            resp = client.get("/events/user/test@user.com")
            assert resp.status_code == 200
