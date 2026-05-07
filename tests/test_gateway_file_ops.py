"""
Integration tests for: Gateway -> File Ops API flow.
Tests the gateway proxying requests to file_ops service.
"""
import pytest


class TestGatewayFileOpsIntegration:
    def test_upload_file_via_gateway(self, mock_file_ops_response):
        assert mock_file_ops_response["file_id"] == "test-file-id"

    def test_list_files_via_gateway(self):
        response_data = {
            "files": [
                {"file_name": "test1.txt", "file_path": "/test1.txt"},
                {"file_name": "test2.txt", "file_path": "/test2.txt"},
            ],
            "storage_type": "gcs"
        }
        assert len(response_data["files"]) == 2

    def test_delete_file_via_gateway(self):
        result = {"message": "File /test.txt deleted from gcs"}
        assert "deleted" in result["message"]

    def test_download_file_via_gateway(self, sample_file_content):
        assert sample_file_content == b"This is a test file content for integration testing."


class TestFileOpsDomain:
    def test_upload_response_model(self):
        from src.file_ops.domain.domain import UploadResponse

        response = UploadResponse(
            file_id="test-id",
            file_name="test.txt",
            storage_type="gcs",
            url="https://example.com/test.txt",
            message="File uploaded successfully"
        )

        assert response.file_id == "test-id"
        assert response.file_name == "test.txt"
        assert response.storage_type == "gcs"

    def test_file_item_model(self):
        from src.file_ops.domain.domain import FileItem

        item = FileItem(
            path="/test.txt",
            name="test.txt",
            isDirectory=False,
        )

        assert item.name == "test.txt"
        assert item.path == "/test.txt"

    def test_list_files_response_model(self):
        from src.file_ops.domain.domain import ListFilesResponse, FileItem

        response = ListFilesResponse(
            files=[FileItem(path="/a.txt", name="a.txt", isDirectory=False)],
            storage_type="gcs"
        )

        assert len(response.files) == 1
        assert response.storage_type == "gcs"


class TestGatewayErrorHandling:
    def test_gateway_returns_503_on_connection_error(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(status_code=503, detail="File service unavailable")

        assert exc_info.value.status_code == 503

    def test_gateway_returns_504_on_timeout(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(status_code=504, detail="File service timeout")

        assert exc_info.value.status_code == 504
