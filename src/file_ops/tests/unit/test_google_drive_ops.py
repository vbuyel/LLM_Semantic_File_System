import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import io
import os
import requests

from adapters.google_drive_ops import GoogleDriveOperations
from adapters.text_extractor import TextExtractorOperations


@pytest.fixture(autouse=True)
def mock_kafka():
    """Mock KafkaOperations singleton."""
    with patch("adapters.google_drive_ops.KafkaOperations") as mock_class:
        mock_instance = MagicMock()
        mock_instance.send_command = AsyncMock()
        mock_instance.send_event = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_drive_service():
    """Mock Google Drive service returned by build()."""
    with patch("adapters.google_drive_ops.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        yield mock_service


def test_chunk_text():
    """Verify text chunking splits by word boundaries under max character limits."""
    extractor = TextExtractorOperations()

    # Short text
    short = "Hello World"
    assert extractor.chunk_text(short, max_chars=20) == [short]

    # Splitting at word boundaries
    text = "one two three four five"
    # max_chars=13 should chunk as: "one two three" (13 chars), "four five" (9 chars)
    chunks = extractor.chunk_text(text, max_chars=13)
    assert chunks == ["one two three", "four five"]

    # Single extremely long word
    long_word = "abcdefghijklmnopqrstuvwxyz"
    assert extractor.chunk_text(long_word, max_chars=5) == [long_word]


@pytest.mark.anyio
async def test_send_chunked_kafka(mock_kafka):
    """Verify chunked text is cleaned, checked for readability, and sent to Kafka."""
    extractor = TextExtractorOperations()
    extractor.kafka = mock_kafka

    # 1. Unreadable text should be skipped
    await extractor.send_chunked_kafka(
        action="upload",
        file_name="bad.txt",
        file_path="root/",
        text="$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$",
        owner="vlad",
        storage_type="drive",
    )
    mock_kafka.send_command.assert_not_called()

    # 2. Readable text should be chunked and sent
    long_readable_text = " ".join(["word"] * 50)  # ~250 chars
    # We pass low max_chars to force chunking. We must make sure chunks are >= 10 chars to be readable.
    with patch.object(extractor, "chunk_text", return_value=["chunk1_longer_than_10_chars", "chunk2_longer_than_10_chars"]):
        await extractor.send_chunked_kafka(
            action="upload",
            file_name="good.txt",
            file_path="root/",
            text=long_readable_text,
            owner="vlad",
            storage_type="drive",
            file_size=100,
        )
        assert mock_kafka.send_command.call_count == 2
        
        # Check command contents
        sent_data = mock_kafka.send_command.call_args_list[0][0][0]
        assert sent_data.action == "upload"
        assert sent_data.file_name == "good.txt"
        assert sent_data.text == "chunk1_longer_than_10_chars"
        assert sent_data.chunk_index == 0


def test_download_file_with_retry_success(mock_drive_service):
    """Verify download retry logic succeeds on second attempt."""
    drive = GoogleDriveOperations(access_token="test-token")
    
    mock_download = MagicMock()
    # First fails, second succeeds
    mock_download.side_effect = [Exception("API error"), (b"data", "file.txt", "text/plain")]
    
    with patch.object(drive, "download_file", mock_download):
        with patch("time.sleep") as mock_sleep:
            content, name, mime = drive._download_file_with_retry("id123")
            assert content == b"data"
            assert mock_download.call_count == 2
            mock_sleep.assert_called_once_with(1)  # wait 2^0 = 1s


def test_download_file_with_retry_exhausted(mock_drive_service):
    """Verify download retry logic raises original exception after exhausting retries."""
    drive = GoogleDriveOperations(access_token="test-token")
    
    mock_download = MagicMock(side_effect=Exception("Connection timed out"))
    
    with patch.object(drive, "download_file", mock_download):
        with patch("time.sleep") as mock_sleep:
            with pytest.raises(Exception) as exc:
                drive._download_file_with_retry("id123", max_retries=3)
            assert "Connection timed out" in str(exc.value)
            assert mock_download.call_count == 3
            assert mock_sleep.call_count == 2  # slept after attempt 1 and 2


@pytest.mark.anyio
async def test_get_file_dir_recursive(mock_drive_service):
    """Verify recursive parent directory construction."""
    drive = GoogleDriveOperations(access_token="test-token")

    # Mock the recursive structure: file -> parent1 -> root (which has no parents)
    mock_get = mock_drive_service.files().get
    
    # Setup mock execute results
    mock_get.return_value.execute.side_effect = [
        {"name": "file.txt", "parents": ["parent1_id"]},
        {"name": "folder1", "parents": ["root_id"]},
        {"name": "My Drive", "parents": []},
    ]

    path = await drive._get_file_dir("file_id")
    assert path == "root/My Drive/folder1/"


@pytest.mark.anyio
async def test_get_file_dir_error_fallback(mock_drive_service):
    """Verify path builder returns "root/" fallback if API fails."""
    drive = GoogleDriveOperations(access_token="test-token")
    mock_drive_service.files().get.side_effect = Exception("API error")
    
    path = await drive._get_file_dir("file_id")
    assert path == "root/"


@pytest.mark.anyio
@patch("requests.get")
async def test_is_already_indexed(mock_get, mock_drive_service):
    """Verify is_already_indexed checks database via HTTP and handles errors gracefully."""
    drive = GoogleDriveOperations(access_token="test-token")

    # 1. Database says exists
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"exists": True}
    mock_get.return_value = mock_resp
    
    assert await drive._is_already_indexed("root/", "test.txt", 100) is True

    # 2. Connection error
    mock_get.side_effect = requests.ConnectionError("Connection lost")
    assert await drive._is_already_indexed("root/", "test.txt", 100) is False


@pytest.mark.anyio
@patch.object(TextExtractorOperations, "extract_text_from_bytes", return_value="drive file content")
async def test_background_vectorise(mock_extract, mock_kafka, mock_drive_service):
    """Verify background vectorisation downloads files, checks db, and sends chunks."""
    drive = GoogleDriveOperations(access_token="test-token")

    items = [
        # Folder item (should be skipped from downloading/indexing)
        {"id": "fold_1", "name": "docs", "mimeType": "application/vnd.google-apps.folder", "size": None},
        # File item
        {"id": "file_1", "name": "my_doc.docx", "mimeType": "application/vnd.openxmlformats-officedocument", "size": "1024"},
    ]

    # Mock DB check to return False (not indexed yet)
    with patch.object(drive, "_is_already_indexed", return_value=False) as mock_db_check:
        with patch.object(drive, "_download_file_with_retry", return_value=(b"file_bytes", "my_doc.docx", "application/vnd.openxmlformats-officedocument")) as mock_down:
            with patch.object(drive, "_get_file_dir", return_value="root/docs/") as mock_dir:
                await drive._background_vectorise(items, owner="vlad", correlation_id="corr-1")
                
                # Check that download was called only for file_1, not the folder fold_1
                mock_down.assert_called_once_with("file_1", "application/vnd.openxmlformats-officedocument", "my_doc.docx")
                mock_extract.assert_called_once_with(b"file_bytes", ".docx")
                
                # Check start/stop events sent to Kafka
                assert mock_kafka.send_event.call_count == 2
                mock_kafka.send_event.assert_any_call(event="Vectorising your cloud files...", owner="vlad", correlation_id="corr-1")
                mock_kafka.send_event.assert_any_call(event="Done! Files are prepared to analyze", owner="vlad", correlation_id="corr-1")


@pytest.mark.anyio
async def test_list_files_triggers_background_vector(mock_drive_service):
    """Verify list_files queries Drive API and schedules background vectorization task."""
    drive = GoogleDriveOperations(access_token="test-token")

    mock_list = mock_drive_service.files().list
    mock_list.return_value.execute.return_value = {
        "files": [
            {"id": "id1", "name": "file1.txt", "mimeType": "text/plain", "size": "50", "modifiedTime": "2026-05-18T12:00:00Z"}
        ]
    }

    with patch("asyncio.create_task") as mock_create_task:
        files = await drive.list_files(owner="vlad", directory_path="/")
        assert len(files) == 1
        assert files[0]["name"] == "file1.txt"
        
        # Verify background task scheduled
        mock_create_task.assert_called_once()


def test_download_google_document_vs_regular_file(mock_drive_service):
    """Verify Google docs are exported using export_media, while regular files use get_media."""
    drive = GoogleDriveOperations(access_token="test-token")

    # Helper mock downloader
    mock_downloader_class = MagicMock()
    mock_downloader = MagicMock()
    mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
    mock_downloader_class.return_value = mock_downloader

    with patch("adapters.google_drive_ops.MediaIoBaseDownload", mock_downloader_class):
        # Case 1: Google Document
        drive.download_file("doc123", mime_type="application/vnd.google-apps.document", file_name="doc")
        mock_drive_service.files().export_media.assert_called_once_with(
            fileId="doc123",
            mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        mock_drive_service.files().get_media.assert_not_called()
        
        # Reset mocks
        mock_drive_service.files().export_media.reset_mock()
        mock_drive_service.files().get_media.reset_mock()
        mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]

        # Case 2: Regular file (e.g., text/plain)
        drive.download_file("file123", mime_type="text/plain", file_name="file.txt")
        mock_drive_service.files().get_media.assert_called_once_with(fileId="file123")
        mock_drive_service.files().export_media.assert_not_called()


@pytest.mark.anyio
async def test_drive_delete_file_success(mock_kafka, mock_drive_service):
    """Verify drive delete deletes file and notifies Kafka."""
    drive = GoogleDriveOperations(access_token="test-token")

    mock_drive_service.files().get.return_value.execute.return_value = {"name": "test.txt", "parents": []}

    await drive.delete_file("file_id_123", owner="vlad")

    mock_drive_service.files().delete.assert_called_once_with(fileId="file_id_123")
    
    # Kafka checked
    mock_kafka.send_command.assert_called_once()
    sent_data = mock_kafka.send_command.call_args[0][0]
    assert sent_data.action == "delete"
    assert sent_data.file_name == "test.txt"
    assert sent_data.owner == "vlad"
    assert sent_data.storage_type == "drive"


@pytest.mark.anyio
async def test_drive_rename_file_success(mock_kafka, mock_drive_service):
    """Verify drive rename updates metadata and notifies Kafka."""
    drive = GoogleDriveOperations(access_token="test-token")

    mock_drive_service.files().get.return_value.execute.return_value = {"name": "old_name.txt", "parents": []}
    mock_drive_service.files().update.return_value.execute.return_value = {"id": "file123", "name": "new_name.txt", "webViewLink": "http://g.co"}

    result = await drive.rename_file("file123", "new_name.txt", owner="vlad")

    mock_drive_service.files().update.assert_called_once_with(
        fileId="file123",
        body={"name": "new_name.txt"},
        fields="id, name, webViewLink"
    )
    
    assert result["file_id"] == "file123"
    assert result["url"] == "http://g.co"
    
    # Kafka checked
    mock_kafka.send_command.assert_called_once()
    sent_data = mock_kafka.send_command.call_args[0][0]
    assert sent_data.action == "rename"
    assert sent_data.file_name == "new_name.txt"
    assert sent_data.old_file_name == "old_name.txt"
    assert sent_data.owner == "vlad"
    assert sent_data.storage_type == "drive"
