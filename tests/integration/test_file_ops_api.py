"""
Integration tests for file_ops FastAPI endpoints.
Uses TestClient to test the HTTP layer with mocked storage backends.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a TestClient with all Kafka/GCS dependencies mocked."""
    with patch("src.file_ops.adapters.kafka.AIOKafkaProducer", return_value=AsyncMock()):
        # Reset singleton
        from src.file_ops.adapters.kafka import KafkaOperations
        KafkaOperations._instance = None
        KafkaOperations._initialized = False

        import importlib
        import src.file_ops.endpoints.main as mod
        importlib.reload(mod)

        mock_gcs = MagicMock()
        mod.gcs_ops = mock_gcs
        mod.kafka_ops = AsyncMock()

        with TestClient(mod.app) as c:
            yield c, mock_gcs

        KafkaOperations._instance = None
        KafkaOperations._initialized = False


class TestHealthEndpoint:
    def test_health_check(self, client):
        c, _ = client
        resp = c.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestListFilesEndpoint:
    def test_list_files_gcs(self, client):
        c, mock_gcs = client
        mock_gcs.list_files.return_value = [
            {"path": "test.txt", "name": "test.txt", "isDirectory": False, "size": 100, "modified": None}
        ]
        resp = c.get("/get_all?path=/", headers={"X-Storage-Source": "gcs"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["storage_type"] == "gcs"
        assert len(data["files"]) == 1

    def test_list_files_unsupported_source(self, client):
        c, _ = client
        resp = c.get("/get_all?path=/", headers={"X-Storage-Source": "s3"})
        assert resp.status_code in (400, 500)  # caught by generic handler


class TestDeleteEndpoint:
    def test_delete_file_gcs(self, client):
        c, mock_gcs = client
        mock_gcs.delete_file = AsyncMock()
        resp = c.delete("/delete?path=test.txt", headers={"X-Storage-Source": "gcs"})
        assert resp.status_code == 200

    def test_delete_unsupported_source(self, client):
        c, _ = client
        resp = c.delete("/delete?path=test.txt", headers={"X-Storage-Source": "s3"})
        assert resp.status_code in (400, 500)


class TestRenameEndpoint:
    def test_rename_gcs(self, client):
        c, mock_gcs = client
        mock_gcs.rename_file = AsyncMock(return_value={
            "file_id": "new.txt", "url": "gs://b/new.txt", "storage_type": "gcs"
        })
        resp = c.put("/rename?path=old.txt&new_name=new.txt",
                     headers={"X-Storage-Source": "gcs"})
        assert resp.status_code == 200

    def test_rename_unsupported_source(self, client):
        c, _ = client
        resp = c.put("/rename?path=old.txt&new_name=new.txt",
                     headers={"X-Storage-Source": "s3"})
        assert resp.status_code in (400, 500)


class TestDownloadEndpoint:
    def test_download_gcs(self, client):
        c, mock_gcs = client
        mock_gcs.download_file.return_value = (b"file content", "test.txt", "text/plain")
        resp = c.get("/download?path=test.txt", headers={"X-Storage-Source": "gcs"})
        assert resp.status_code == 200
        assert resp.content == b"file content"

    def test_download_drive_no_token(self, client):
        c, _ = client
        resp = c.get("/download?path=file-id", headers={"X-Storage-Source": "drive"})
        assert resp.status_code == 401
