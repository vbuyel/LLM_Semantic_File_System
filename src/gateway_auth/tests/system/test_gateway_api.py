from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
import requests

from v1.main import app
from domain.settings import settings


@pytest.fixture
def client():
    return TestClient(app)


@patch("v1.gateway_router.requests.post")
def test_call_ai_agent_success(mock_post, client):
    """Verify calling AI agent works, forwarding owner and correlation ID."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_200_OK
    mock_response.json.return_value = {"text": "Hello from AI!"}
    mock_post.return_value = mock_response

    response = client.post(
        "/gateway/ai_agent",
        json={"text": "Hello agent"},
        headers={"X-Owner": "user-bob", "X-Correlation-ID": "test-correlation-abc"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"text": "Hello from AI!"}
    
    # Check that downstream post was called with correct parameters
    mock_post.assert_called_once()
    kwargs = mock_post.call_args[1]
    assert kwargs["url"] == f"{settings.AGENT_SERVER}/get_response"
    assert kwargs["json"] == {
        "text": "Hello agent",
        "owner": "user-bob",
        "correlation_id": "test-correlation-abc"
    }


@patch("v1.gateway_router.requests.post")
def test_call_ai_agent_service_unavailable(mock_post, client):
    """Verify that a ConnectionError from AI agent service returns 503 Service Unavailable."""
    mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

    response = client.post(
        "/gateway/ai_agent",
        json={"text": "Hello agent"}
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "File service unavailable" in response.json()["detail"]


@patch("v1.gateway_router.requests.post")
def test_call_ai_agent_timeout(mock_post, client):
    """Verify that a Timeout from AI agent service returns 504 Gateway Timeout."""
    mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

    response = client.post(
        "/gateway/ai_agent",
        json={"text": "Hello agent"}
    )
    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert "File service timeout" in response.json()["detail"]


@patch("v1.gateway_router.requests.post")
def test_call_ai_agent_downstream_error(mock_post, client):
    """Verify downstream errors are raised correctly with details."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_400_BAD_REQUEST
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"detail": "Agent did not understand"}
    mock_post.return_value = mock_response

    response = client.post(
        "/gateway/ai_agent",
        json={"text": "invalid prompt"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Agent did not understand"


@patch("v1.gateway_router.requests.get")
def test_get_objects_success(mock_get, client):
    """Verify get_objects relays path and custom storage headers."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_200_OK
    mock_response.json.return_value = {
        "files": [{"path": "/foo.txt", "name": "foo.txt", "isDirectory": False, "size": 42}],
        "storage_type": "gcs"
    }
    mock_get.return_value = mock_response

    response = client.get(
        "/gateway/get_objects",
        params={"path": "/docs"},
        headers={
            "X-Owner": "bob",
            "X-Storage-Source": "gcs",
            "X-Auth-Provider": "local",
            "Authorization": "Bearer tok"
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["storage_type"] == "gcs"
    assert len(data["files"]) == 1

    # Verify requests.get call arguments
    mock_get.assert_called_once()
    kwargs = mock_get.call_args[1]
    assert kwargs["url"] == f"{settings.FILE_OPS_SERVER}/get_all"
    assert kwargs["params"] == {"path": "/docs"}
    assert kwargs["headers"]["X-Owner"] == "bob"
    assert kwargs["headers"]["X-Storage-Source"] == "gcs"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


@patch("v1.gateway_router.requests.post")
def test_upload_object_success(mock_post, client):
    """Verify that uploading a file transfers correct file parts and headers."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_200_OK
    mock_response.json.return_value = {"message": "Uploaded successfully"}
    mock_post.return_value = mock_response

    file_payload = {"file": ("document.txt", b"secret text content", "text/plain")}
    response = client.post(
        "/gateway/upload_object",
        files=file_payload,
        headers={"X-Owner": "test-owner"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Uploaded successfully"}

    mock_post.assert_called_once()
    kwargs = mock_post.call_args[1]
    assert kwargs["url"] == f"{settings.FILE_OPS_SERVER}/upload"
    assert kwargs["headers"]["X-Owner"] == "test-owner"
    assert "file" in kwargs["files"]


@patch("v1.gateway_router.requests.delete")
def test_delete_object_success(mock_delete, client):
    """Verify deleting an object forwards the request to downstream service."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_200_OK
    mock_response.json.return_value = {"message": "Deleted"}
    mock_delete.return_value = mock_response

    response = client.delete(
        "/gateway/delete_object",
        params={"path": "/old_file.txt"},
        headers={"X-Owner": "del-owner"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Deleted"}

    mock_delete.assert_called_once()
    kwargs = mock_delete.call_args[1]
    assert kwargs["url"] == f"{settings.FILE_OPS_SERVER}/delete"
    assert kwargs["params"] == {"path": "/old_file.txt"}
    assert kwargs["headers"]["X-Owner"] == "del-owner"


@patch("v1.gateway_router.requests.put")
def test_rename_object_success(mock_rename, client):
    """Verify renaming an object forwards path, new name, and headers."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_200_OK
    mock_response.json.return_value = {"message": "Renamed"}
    mock_rename.return_value = mock_response

    response = client.put(
        "/gateway/rename_object",
        params={"path": "/file.txt", "new_name": "/new_file.txt"},
        headers={"X-Owner": "rename-owner"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Renamed"}

    mock_rename.assert_called_once()
    kwargs = mock_rename.call_args[1]
    assert kwargs["url"] == f"{settings.FILE_OPS_SERVER}/rename"
    assert kwargs["params"] == {"path": "/file.txt", "new_name": "/new_file.txt"}
    assert kwargs["headers"]["X-Owner"] == "rename-owner"


@patch("v1.gateway_router.requests.get")
def test_download_object_success(mock_get, client):
    """Verify download forwards the request and streams content back with headers."""
    mock_response = MagicMock()
    mock_response.status_code = status.HTTP_200_OK
    mock_response.content = b"streamable data content"
    mock_response.headers = {
        "content-type": "application/pdf",
        "Content-Disposition": 'attachment; filename="report.pdf"'
    }
    mock_get.return_value = mock_response

    response = client.get(
        "/gateway/download_object",
        params={"path": "/report.pdf"},
        headers={"X-Owner": "downloader"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"streamable data content"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="report.pdf"'

    mock_get.assert_called_once()
    kwargs = mock_get.call_args[1]
    assert kwargs["url"] == f"{settings.FILE_OPS_SERVER}/download"
    assert kwargs["params"] == {"path": "/report.pdf"}
    assert kwargs["headers"]["X-Owner"] == "downloader"
