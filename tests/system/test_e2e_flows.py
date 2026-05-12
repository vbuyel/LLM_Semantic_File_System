"""
System tests: end-to-end flows across multiple services.
All external dependencies (Kafka, DBs, Google APIs) are mocked.
These tests validate that multi-service interactions produce correct outcomes.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

pytestmark = pytest.mark.system


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def _make_gateway_client(monkeypatch):
    """Create a gateway TestClient with mocked settings."""
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
        return TestClient(app)


# -----------------------------------------------------------------------
# Test: Gateway → File Ops flow (upload via proxy)
# -----------------------------------------------------------------------
class TestGatewayToFileOpsUploadFlow:
    """Simulate: User uploads file via Gateway → Gateway proxies to File Ops."""

    def test_upload_via_gateway(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        with patch("src.gateway_auth.endpoints.gateway_router.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "file_id": "abc", "file_name": "test.txt",
                "storage_type": "gcs", "url": "gs://b/test.txt",
                "message": "File uploaded to gcs"
            }
            mock_post.return_value = mock_resp

            import io
            files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
            resp = client.post("/gateway/upload_object", files=files,
                               headers={"X-Storage-Source": "gcs"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["file_id"] == "abc"
            assert data["storage_type"] == "gcs"


# -----------------------------------------------------------------------
# Test: Gateway → File Ops flow (list → delete)
# -----------------------------------------------------------------------
class TestGatewayListThenDeleteFlow:
    """Simulate: User lists files, then deletes one via Gateway."""

    def test_list_then_delete(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)

        # Step 1: List files
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "files": [
                    {"path": "doc.pdf", "name": "doc.pdf", "isDirectory": False,
                     "size": 1000, "modified": None}
                ],
                "storage_type": "gcs"
            }
            mock_get.return_value = mock_resp
            resp = client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 200
            files = resp.json()["files"]
            assert len(files) == 1
            file_path = files[0]["path"]

        # Step 2: Delete that file
        with patch("src.gateway_auth.endpoints.gateway_router.requests.delete") as mock_del:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"message": f"File {file_path} deleted"}
            mock_del.return_value = mock_resp
            resp = client.delete(f"/gateway/delete_object?path={file_path}")
            assert resp.status_code == 200


# -----------------------------------------------------------------------
# Test: Gateway → LLM Agent flow (AI search)
# -----------------------------------------------------------------------
class TestGatewayToLLMFlow:
    """Simulate: User asks AI question via Gateway → routed to LLM service."""

    def test_ai_search_flow(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        with patch("src.gateway_auth.endpoints.gateway_router.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"text": "Based on your files, here is the answer..."}
            mock_post.return_value = mock_resp

            resp = client.post("/gateway/ai_agent", json={"text": "Find my quarterly report"})
            assert resp.status_code == 200
            assert "answer" in resp.json()["text"]


# -----------------------------------------------------------------------
# Test: Gateway → File Ops rename flow
# -----------------------------------------------------------------------
class TestGatewayRenameFlow:
    """Simulate: User renames a file via Gateway."""

    def test_rename_flow(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        with patch("src.gateway_auth.endpoints.gateway_router.requests.put") as mock_put:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": "File renamed to new_report.pdf",
                "file_id": "new_report.pdf",
                "url": "gs://bucket/new_report.pdf",
                "storage_type": "gcs"
            }
            mock_put.return_value = mock_resp

            resp = client.put("/gateway/rename_object?path=old_report.pdf&new_name=new_report.pdf")
            assert resp.status_code == 200
            assert "renamed" in resp.json()["message"].lower()


# -----------------------------------------------------------------------
# Test: Gateway → File Ops download flow
# -----------------------------------------------------------------------
class TestGatewayDownloadFlow:
    """Simulate: User downloads a file via Gateway."""

    def test_download_flow(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"PDF binary content here"
            mock_resp.headers = {
                "content-type": "application/pdf",
                "Content-Disposition": 'attachment; filename="report.pdf"'
            }
            mock_get.return_value = mock_resp

            resp = client.get("/gateway/download_object?path=report.pdf")
            assert resp.status_code == 200
            assert len(resp.content) > 0


# -----------------------------------------------------------------------
# Test: Error propagation across services
# -----------------------------------------------------------------------
class TestErrorPropagation:
    """Verify errors from downstream services are properly relayed."""

    def test_file_ops_error_propagated(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.json.return_value = {"detail": "File not found"}
            mock_get.return_value = mock_resp

            resp = client.get("/gateway/get_objects?path=/nonexistent")
            assert resp.status_code == 404

    def test_service_down_returns_503(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        import requests
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()
            resp = client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 503

    def test_service_timeout_returns_504(self, monkeypatch):
        client = _make_gateway_client(monkeypatch)
        import requests
        with patch("src.gateway_auth.endpoints.gateway_router.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            resp = client.get("/gateway/get_objects?path=/")
            assert resp.status_code == 504
