import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock aiokafka to prevent event loop issues during module import
mock_aiokafka = MagicMock()
mock_aiokafka.AIOKafkaProducer = MagicMock()
mock_aiokafka.admin = MagicMock()
sys.modules["aiokafka"] = mock_aiokafka
sys.modules["aiokafka.admin"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from fastapi import status
import io
import os

from v1.main import app, _get_current_user, gcs_ops


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_kafka():
    """Mock Kafka operations to prevent real connections during system tests."""
    with patch("v1.main.kafka_ops") as mock_kafka_ops:
        mock_kafka_ops.start = AsyncMock()
        mock_kafka_ops.stop = AsyncMock()
        yield mock_kafka_ops


def test_health_endpoint(client):
    """Verify /health returns status ok."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_get_all_gcs_success(client):
    """Verify listing files from GCS works with stubbed auth."""
    mock_files = [
        {"path": "file1.txt", "name": "file1.txt", "isDirectory": False, "size": 100, "modified": "2026-05-18T10:00:00"},
        {"path": "folder1/", "name": "folder1", "isDirectory": True, "size": None, "modified": None},
    ]

    # Override authentication dependency
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "local",
        "storage_source": "gcs",
        "token": None,
        "correlation_id": "corr-123",
    }

    with patch.object(gcs_ops, "list_files", return_value=mock_files) as mock_list:
        response = client.get("/get_all", params={"path": "/"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["storage_type"] == "gcs"
        assert len(data["files"]) == 2
        assert data["files"][0]["name"] == "file1.txt"
        assert data["files"][0]["isDirectory"] is False
        assert data["files"][1]["name"] == "folder1"
        assert data["files"][1]["isDirectory"] is True
        
        mock_list.assert_called_once_with("/")


def test_get_all_drive_missing_token(client):
    """Verify listing Google Drive files without a token raises 401."""
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "google",
        "storage_source": "drive",
        "token": None,  # Missing token!
        "correlation_id": "corr-123",
    }

    response = client.get("/get_all", params={"path": "/"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Access token required" in response.json()["detail"]


@pytest.mark.anyio
@patch("v1.main.GoogleDriveOperations")
async def test_get_all_drive_success(mock_drive_class, client):
    """Verify listing Google Drive files returns correct structure when token is present."""
    mock_drive_instance = MagicMock()
    mock_drive_instance.list_files = AsyncMock(return_value=[
        {"path": "id_1", "name": "drive_doc.pdf", "isDirectory": False, "size": 250, "modified": "2026-05-18T11:00:00"}
    ])
    mock_drive_class.return_value = mock_drive_instance

    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "google",
        "storage_source": "drive",
        "token": "valid_token",
        "correlation_id": "corr-999",
    }

    response = client.get("/get_all", params={"path": "folder_id"})
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["storage_type"] == "drive"
    assert len(data["files"]) == 1
    assert data["files"][0]["name"] == "drive_doc.pdf"
    
    mock_drive_instance.list_files.assert_called_once_with(
        owner="vlad", directory_path="folder_id", correlation_id="corr-999"
    )


def test_upload_file_gcs_success(client):
    """Verify uploading a file to GCS works, checks temporary file cleanup, and returns UploadResponse."""
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "local",
        "storage_source": "gcs",
        "token": None,
    }

    mock_upload_result = {
        "file_id": "uploaded_test.txt",
        "url": "gs://test-bucket/uploaded_test.txt",
        "storage_type": "gcs",
    }

    with patch.object(gcs_ops, "upload_file", return_value=mock_upload_result) as mock_upload:
        # Create a mock file in memory
        file_content = b"Some sample text for upload"
        file_to_upload = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

        # We'll spy on os.path.exists and os.remove to verify temp file cleanup
        with patch("os.path.exists", wraps=os.path.exists) as mock_exists:
            with patch("os.remove", wraps=os.remove) as mock_remove:
                response = client.post("/upload", files=file_to_upload)

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["file_id"] == "uploaded_test.txt"
                assert data["file_name"] == "test.txt"
                assert data["storage_type"] == "gcs"
                assert data["url"] == "gs://test-bucket/uploaded_test.txt"
                assert data["message"] == "File uploaded to gcs"

                # Verify GCS upload called with temp path
                mock_upload.assert_called_once()
                temp_path = mock_upload.call_args[1]["source_path"]
                assert temp_path.endswith("/test.txt")

                # Verify cleanup happened
                mock_exists.assert_any_call(temp_path)
                mock_remove.assert_called_with(temp_path)


@patch("v1.main.GoogleDriveOperations")
def test_upload_file_drive_success(mock_drive_class, client):
    """Verify uploading a file to Google Drive succeeds when token is present."""
    mock_drive_instance = MagicMock()
    mock_drive_instance.upload_file = AsyncMock(return_value={
        "file_id": "drive_id_456",
        "url": "https://drive.google.com/test",
        "storage_type": "drive",
    })
    mock_drive_class.return_value = mock_drive_instance

    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "google",
        "storage_source": "drive",
        "token": "valid_drive_token",
    }

    file_to_upload = {"file": ("test.docx", io.BytesIO(b"docx content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    
    response = client.post("/upload", files=file_to_upload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["file_id"] == "drive_id_456"
    assert data["storage_type"] == "drive"
    assert data["url"] == "https://drive.google.com/test"
    
    mock_drive_instance.upload_file.assert_called_once()


def test_delete_file_gcs_success(client):
    """Verify GCS file deletion."""
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "local",
        "storage_source": "gcs",
    }

    with patch.object(gcs_ops, "delete_file", return_value=None) as mock_delete:
        response = client.delete("/delete", params={"path": "root/del.txt"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "File root/del.txt deleted from gcs"
        mock_delete.assert_called_once_with("root/del.txt", owner="vlad")


def test_rename_file_gcs_success(client):
    """Verify GCS file renaming."""
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "local",
        "storage_source": "gcs",
    }

    mock_result = {
        "file_id": "new_name.txt",
        "url": "gs://test-bucket/new_name.txt",
        "storage_type": "gcs",
    }

    with patch.object(gcs_ops, "rename_file", return_value=mock_result) as mock_rename:
        response = client.put("/rename", params={"path": "root/old.txt", "new_name": "new_name.txt"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "File renamed to new_name.txt"
        assert data["file_id"] == "new_name.txt"
        assert data["url"] == "gs://test-bucket/new_name.txt"
        
        mock_rename.assert_called_once_with("root/old.txt", "new_name.txt", owner="vlad")


def test_rename_file_not_found(client):
    """Verify rename returns 404 if file is not found."""
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "local",
        "storage_source": "gcs",
    }

    with patch.object(gcs_ops, "rename_file", side_effect=FileNotFoundError("Blob not found")):
        response = client.put("/rename", params={"path": "root/missing.txt", "new_name": "new.txt"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Blob not found" in response.json()["detail"]


def test_download_file_gcs_success(client):
    """Verify GCS file download returns StreamingResponse with proper headers."""
    app.dependency_overrides[_get_current_user] = lambda: {
        "owner": "vlad",
        "provider": "local",
        "storage_source": "gcs",
    }

    mock_content = b"downloaded binary content"
    with patch.object(gcs_ops, "download_file", return_value=(mock_content, "downloaded.txt", "text/plain")) as mock_download:
        response = client.get("/download", params={"path": "root/downloaded.txt"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == mock_content
        assert response.headers["Content-Disposition"] == 'attachment; filename="downloaded.txt"'
        assert response.headers["Content-Length"] == str(len(mock_content))
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        mock_download.assert_called_once_with("root/downloaded.txt")
