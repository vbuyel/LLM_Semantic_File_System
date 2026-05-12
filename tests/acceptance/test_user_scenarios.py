"""
Acceptance tests: verify user-facing scenarios work as expected.
Written from the end-user perspective — "As a user, I can..."
All external services are mocked.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

pytestmark = pytest.mark.acceptance


@pytest.fixture
def gateway_client(monkeypatch):
    """Gateway TestClient with all env vars configured."""
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("OAUTH_GOOGLE_REDIRECT_URI", "http://localhost/cb")
    monkeypatch.setenv("OAUTH_GOOGLE_BASE_URL", "http://localhost")
    monkeypatch.setenv("AGENT_SERVER", "http://localhost:8001")
    monkeypatch.setenv("FILE_OPS_SERVER", "http://localhost:8002")
    monkeypatch.setenv("EVENT_DB_URL", "http://localhost:8003")
    monkeypatch.setenv("EVENT_DB_WS_URL", "ws://localhost:8003/ws/gateway")

    with patch("src.gateway_auth.adapters.events_ws.relay_events_from_eventdb"):
        from src.gateway_auth.endpoints.main import app
        with TestClient(app) as c:
            yield c


class TestUserCanAuthenticate:
    """AC: User can initiate Google OAuth login flow."""

    def test_user_gets_redirected_to_google(self, gateway_client):
        with patch("src.gateway_auth.endpoints.oauth_router.generate_google_oauth_redirect_uri") as mock_gen:
            mock_gen.return_value = "https://accounts.google.com/o/oauth2/v2/auth?test=1"
            resp = gateway_client.get("/auth/google/url", follow_redirects=False)
            assert resp.status_code == 302
            assert "accounts.google.com" in resp.headers.get("location", "")


class TestUserCanListFiles:
    """AC: User can see their files in cloud storage."""

    def test_user_sees_files(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "files": [
                    {"path": "report.pdf", "name": "report.pdf",
                     "isDirectory": False, "size": 2048, "modified": "2026-01-01"},
                    {"path": "photos/", "name": "photos",
                     "isDirectory": True, "size": None, "modified": None},
                ],
                "storage_type": "gcs"
            }
            mock_get.return_value = mock_resp

            resp = gateway_client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 200
            files = resp.json()["files"]
            assert len(files) == 2
            names = [f["name"] for f in files]
            assert "report.pdf" in names
            assert "photos" in names

    def test_user_sees_empty_storage(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"files": [], "storage_type": "gcs"}
            mock_get.return_value = mock_resp

            resp = gateway_client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 200
            assert resp.json()["files"] == []


class TestUserCanUploadFile:
    """AC: User can upload a file to cloud storage."""

    def test_user_uploads_file(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "file_id": "report.pdf", "file_name": "report.pdf",
                "storage_type": "gcs", "url": "gs://bucket/report.pdf",
                "message": "File uploaded to gcs"
            }
            mock_post.return_value = mock_resp

            files = {"file": ("report.pdf", io.BytesIO(b"%PDF-content"), "application/pdf")}
            resp = gateway_client.post("/gateway/upload_object", files=files,
                                        headers={"X-Storage-Source": "gcs"})
            assert resp.status_code == 200
            assert resp.json()["file_name"] == "report.pdf"
            assert resp.json()["message"] == "File uploaded to gcs"


class TestUserCanDeleteFile:
    """AC: User can delete a file from cloud storage."""

    def test_user_deletes_file(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.delete") as mock_del:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"message": "File report.pdf deleted from gcs"}
            mock_del.return_value = mock_resp

            resp = gateway_client.delete("/gateway/delete_object?path=report.pdf")
            assert resp.status_code == 200
            assert "deleted" in resp.json()["message"].lower()


class TestUserCanRenameFile:
    """AC: User can rename a file in cloud storage."""

    def test_user_renames_file(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.put") as mock_put:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": "File renamed to final_report.pdf",
                "file_id": "final_report.pdf",
                "url": "gs://bucket/final_report.pdf",
                "storage_type": "gcs"
            }
            mock_put.return_value = mock_resp

            resp = gateway_client.put(
                "/gateway/rename_object?path=draft.pdf&new_name=final_report.pdf")
            assert resp.status_code == 200
            assert "final_report" in resp.json()["message"]


class TestUserCanDownloadFile:
    """AC: User can download a file from cloud storage."""

    def test_user_downloads_file(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"%PDF-1.4 file binary content"
            mock_resp.headers = {
                "content-type": "application/pdf",
                "Content-Disposition": 'attachment; filename="report.pdf"'
            }
            mock_get.return_value = mock_resp

            resp = gateway_client.get("/gateway/download_object?path=report.pdf")
            assert resp.status_code == 200
            assert len(resp.content) > 0


class TestUserCanAskAI:
    """AC: User can ask the AI agent a question and get a response."""

    def test_user_asks_ai_question(self, gateway_client):
        with patch("src.gateway_auth.endpoints.gateway_router.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "text": "Based on your quarterly report, revenue increased by 15%."
            }
            mock_post.return_value = mock_resp

            resp = gateway_client.post("/gateway/ai_agent",
                                        json={"text": "What does my quarterly report say about revenue?"})
            assert resp.status_code == 200
            assert "revenue" in resp.json()["text"].lower()


class TestUserCanViewEvents:
    """AC: User can see recent activity events."""

    def test_user_sees_recent_events(self, gateway_client):
        from unittest.mock import AsyncMock
        import httpx

        mock_r = MagicMock()
        mock_r.json.return_value = {
            "events": [
                {"id": 1, "owner": "user@test.com", "event": "uploaded", "created_at": "2026-01-01"},
                {"id": 2, "owner": "user@test.com", "event": "deleted", "created_at": "2026-01-02"},
            ]
        }
        mock_r.raise_for_status = MagicMock()

        mock_ac = AsyncMock()
        mock_ac.get = AsyncMock(return_value=mock_r)
        mock_ac.__aenter__.return_value = mock_ac

        with patch("src.gateway_auth.endpoints.events_router.httpx.AsyncClient", return_value=mock_ac):
            resp = gateway_client.get("/events/user/user@test.com")
            assert resp.status_code == 200


class TestUserGetsProperErrors:
    """AC: User gets meaningful error messages when things go wrong."""

    def test_service_unavailable_message(self, gateway_client):
        import requests
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()
            resp = gateway_client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["detail"].lower()

    def test_timeout_message(self, gateway_client):
        import requests
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            resp = gateway_client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 504
            assert "timeout" in resp.json()["detail"].lower()
