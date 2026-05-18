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


class TestGoogleDriveChunkText:
    def test_chunk_text_small_text(self):
        from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations
        text = "short text"
        chunks = GoogleDriveOperations._chunk_text(text, max_chars=10)
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_chunk_text_exactly_at_limit(self):
        from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations
        text = "1234567890"
        chunks = GoogleDriveOperations._chunk_text(text, max_chars=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_multiple_chunks(self):
        from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations
        text = "word " * 100
        chunks = GoogleDriveOperations._chunk_text(text, max_chars=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100

    def test_chunk_text_respects_word_boundaries(self):
        from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations
        text = "hello world foo bar"
        chunks = GoogleDriveOperations._chunk_text(text, max_chars=11)
        for chunk in chunks:
            assert not chunk.endswith(" ") or chunk == chunks[-1]


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
        mock_kafka.send_command.assert_awaited()


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


class TestGoogleDriveGetFileDir:
    @pytest.mark.asyncio
    async def test_get_file_dir_nested(self, drive_ops):
        ops, mock_service, _ = drive_ops
        mock_files = MagicMock()

        mock_files.get.return_value.execute.side_effect = [
            {"name": "file.pdf", "parents": ["folder-id"]},
            {"name": "My Folder", "parents": []},
        ]
        mock_service.files.return_value = mock_files

        result = await ops._get_file_dir("file-id")
        assert result.startswith("root/")
        assert "My Folder" in result

    @pytest.mark.asyncio
    async def test_get_file_dir_error(self, drive_ops):
        ops, mock_service, _ = drive_ops
        mock_files = MagicMock()
        mock_files.get.return_value.execute.side_effect = Exception("API Error")
        mock_service.files.return_value = mock_files

        result = await ops._get_file_dir("file-id")
        assert result == "root/"


class TestGoogleDriveBackgroundVectorise:
    @pytest.mark.asyncio
    async def test_background_vectorise_skips_already_indexed(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.get.return_value.execute.return_value = {"name": "doc.pdf", "parents": []}
        mock_service.files.return_value = mock_files

        with patch.object(ops, '_is_already_indexed', return_value=True):
            await ops._background_vectorise(
                [{"id": "123", "name": "doc.pdf", "mimeType": "application/pdf", "size": "100"}],
                owner="test@test.com"
            )
            mock_kafka.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_background_vectorise_processes_files(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.get.return_value.execute.return_value = {"name": "doc.pdf", "parents": []}
        mock_service.files.return_value = mock_files

        with patch.object(ops, '_is_already_indexed', return_value=False):
            with patch("src.file_ops.adapters.google_drive_ops.MediaIoBaseDownload"):
                mock_blob = MagicMock()
                mock_blob.next_chunk.return_value = (None, True)
                mock_service.files.return_value = mock_files

                await ops._background_vectorise(
                    [{"id": "123", "name": "doc.pdf", "mimeType": "application/pdf", "size": "100"}],
                    owner="test@test.com"
                )


class TestGoogleDriveSendChunkedKafka:
    @pytest.mark.asyncio
    async def test_send_chunked_kafka_filters_unreadable(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        with patch("src.file_ops.adapters.google_drive_ops.is_readable", return_value=False):
            await ops._send_chunked_kafka(
                action="upload",
                file_name="test.pdf",
                file_path="root/",
                text=" unreadable ",
                owner="test@test.com",
                storage_type="drive",
                file_size=100
            )
            mock_kafka.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_chunked_kafka_splits_long_text(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        long_text = "word " * 1000
        with patch("src.file_ops.adapters.google_drive_ops.is_readable", return_value=True):
            await ops._send_chunked_kafka(
                action="upload",
                file_name="test.pdf",
                file_path="root/",
                text=long_text,
                owner="test@test.com",
                storage_type="drive",
                file_size=5000
            )
            assert mock_kafka.send_command.call_count > 1


class TestGoogleDriveErrorHandling:
    @pytest.mark.asyncio
    async def test_upload_file_error_handling(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.create.return_value.execute.side_effect = Exception("Upload failed")
        mock_service.files.return_value = mock_files

        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test")
            temp_path = f.name

        try:
            result = await ops.upload_file(temp_path)
            assert result is not None
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_delete_file_kafka_failure(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.delete.return_value.execute.return_value = None
        mock_service.files.return_value = mock_files
        mock_kafka.send_command.side_effect = Exception("Kafka error")

        await ops.delete_file("file-id", owner="test@test.com")

    @pytest.mark.asyncio
    async def test_rename_file_kafka_failure(self, drive_ops):
        ops, mock_service, mock_kafka = drive_ops
        mock_files = MagicMock()
        mock_files.update.return_value.execute.return_value = {
            "id": "123", "name": "new.txt", "webViewLink": "http://link"
        }
        mock_service.files.return_value = mock_files
        mock_kafka.send_command.side_effect = Exception("Kafka error")

        result = await ops.rename_file("file-id", "new.txt", owner="test@test.com")
        assert result["file_id"] == "123"