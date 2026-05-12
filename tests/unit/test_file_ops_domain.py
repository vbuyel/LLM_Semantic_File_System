"""
Unit tests for src.file_ops.domain.domain models.
"""
import pytest
from src.file_ops.domain.domain import (
    UploadResponse,
    FileItem,
    ListFilesResponse,
    UploadObject,
    ObjectUploaded,
    SendToKafka,
)


pytestmark = pytest.mark.unit


class TestUploadResponse:
    def test_create_upload_response(self):
        resp = UploadResponse(
            file_id="abc123",
            file_name="test.pdf",
            storage_type="gcs",
            url="gs://bucket/test.pdf",
            message="File uploaded",
        )
        assert resp.file_id == "abc123"
        assert resp.storage_type == "gcs"

    def test_upload_response_optional_url(self):
        resp = UploadResponse(
            file_id="id", file_name="f.txt", storage_type="drive", message="ok"
        )
        assert resp.url is None

    def test_upload_response_serialization(self):
        resp = UploadResponse(
            file_id="x", file_name="n", storage_type="gcs", message="m"
        )
        data = resp.model_dump()
        assert "file_id" in data
        assert "url" in data


class TestFileItem:
    def test_create_file_item_directory(self):
        item = FileItem(path="/docs/", name="docs", isDirectory=True)
        assert item.isDirectory is True
        assert item.size is None

    def test_create_file_item_file(self):
        item = FileItem(
            path="/docs/report.pdf",
            name="report.pdf",
            isDirectory=False,
            size=1024,
            modified="2026-01-01T00:00:00Z",
        )
        assert item.isDirectory is False
        assert item.size == 1024


class TestListFilesResponse:
    def test_list_files_response(self):
        files = [
            FileItem(path="/a.txt", name="a.txt", isDirectory=False),
            FileItem(path="/dir/", name="dir", isDirectory=True),
        ]
        resp = ListFilesResponse(files=files, storage_type="gcs")
        assert len(resp.files) == 2
        assert resp.storage_type == "gcs"

    def test_empty_list(self):
        resp = ListFilesResponse(files=[], storage_type="drive")
        assert resp.files == []


class TestUploadObject:
    def test_create_upload_object(self):
        obj = UploadObject(
            file_name="test.txt",
            file_path="/tmp/test.txt",
            text="Hello world",
            owner="user@test.com",
            storage_type="gcs",
        )
        assert obj.file_name == "test.txt"
        assert obj.owner == "user@test.com"

    def test_default_storage_type(self):
        obj = UploadObject(file_name="f", file_path="/p", text="t")
        assert obj.storage_type == "gcs"

    def test_optional_owner(self):
        obj = UploadObject(file_name="f", file_path="/p", text="t")
        assert obj.owner is None


class TestObjectUploaded:
    def test_create_object_uploaded(self):
        obj = ObjectUploaded(file_name="file.txt", chunks_added=5, storage_type="gcs")
        assert obj.chunks_added == 5

    def test_default_chunks(self):
        obj = ObjectUploaded(file_name="f")
        assert obj.chunks_added == 0
        assert obj.storage_type == "gcs"


class TestSendToKafka:
    def test_create_send_to_kafka(self):
        msg = SendToKafka(
            action="upload",
            file_name="test.pdf",
            file_path="/tmp/test.pdf",
            text="content",
            owner="user",
            storage_type="gcs",
        )
        assert msg.action == "upload"
        assert msg.owner == "user"

    def test_default_values(self):
        msg = SendToKafka(action="delete", file_name="f", file_path="/p")
        assert msg.text == ""
        assert msg.owner is None
        assert msg.storage_type == "unknown"

    def test_serialization(self):
        msg = SendToKafka(action="rename", file_name="f", file_path="/p")
        data = msg.model_dump()
        assert data["action"] == "rename"
        assert data["storage_type"] == "unknown"
