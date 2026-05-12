"""
Unit tests for src.file_ops.adapters.google_drive_ops (GoogleDriveOperations).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_kafka():
    with patch("src.file_ops.adapters.google_drive_ops.KafkaOperations") as MockK:
        mock_instance = AsyncMock()
        MockK.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def drive_ops(mock_kafka):
    with patch("src.file_ops.adapters.google_drive_ops.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        with patch("src.file_ops.adapters.google_drive_ops.Credentials"):
            from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations
            ops = GoogleDriveOperations(access_token="fake-token")
            yield ops, mock_service, mock_kafka


class TestGoogleDriveInit:
    def test_service_created(self, drive_ops):
        ops, mock_service, _ = drive_ops
        assert ops.service is mock_service

    def test_access_token_stored(self, drive_ops):
        ops, _, _ = drive_ops
        assert ops._access_token == "fake-token"


class TestGoogleDriveListFiles:
    def test_list_files_root(self, drive_ops):
        ops, mock_service, _ = drive_ops
        mock_files = MagicMock()
        mock_files.list.return_value.execute.return_value = {
            "files": [
                {"id": "1", "name": "doc.pdf", "mimeType": "application/pdf", "size": "500", "modifiedTime": "2026-01-01"},
                {"id": "2", "name": "folder", "mimeType": "application/vnd.google-apps.folder"},
            ]
        }
        mock_service.files.return_value = mock_files
        result = ops.list_files("/")
        assert len(result) == 2
        assert result[1]["isDirectory"] is True
        assert result[0]["isDirectory"] is False

    def test_list_files_empty(self, drive_ops):
        ops, mock_service, _ = drive_ops
        mock_files = MagicMock()
        mock_files.list.return_value.execute.return_value = {"files": []}
        mock_service.files.return_value = mock_files
        result = ops.list_files("/")
        assert result == []


class TestGoogleDriveDownload:
    def test_download_regular_file(self, drive_ops):
        ops, mock_service, _ = drive_ops
        mock_files = MagicMock()
        mock_files.get.return_value.execute.return_value = {
            "name": "test.pdf", "mimeType": "application/pdf"
        }
        mock_media = MagicMock()
        mock_files.get_media.return_value = mock_media
        mock_service.files.return_value = mock_files

        with patch("src.file_ops.adapters.google_drive_ops.MediaIoBaseDownload") as MockDL:
            mock_dl = MagicMock()
            mock_dl.next_chunk.return_value = (None, True)
            MockDL.return_value = mock_dl
            content, name, mime = ops.download_file("file-id-123")
            assert name == "test.pdf"
            assert mime == "application/pdf"


class TestGoogleDriveDelete:
    @pytest.mark.asyncio
    async def test_delete_sends_kafka(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.delete.return_value.execute.return_value = None
        mock_service.files.return_value = mock_files
        await ops.delete_file("file-id", owner="user@test.com")
        mock_kafka.send_start_event.assert_awaited_once()
        mock_kafka.send_command.assert_awaited_once()


class TestGoogleDriveRename:
    @pytest.mark.asyncio
    async def test_rename_returns_result(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.update.return_value.execute.return_value = {
            "id": "file-id", "name": "new_name.txt", "webViewLink": "https://link"
        }
        mock_service.files.return_value = mock_files
        result = await ops.rename_file("file-id", "new_name.txt", owner="u")
        assert result["file_id"] == "file-id"
        assert result["storage_type"] == "drive"
