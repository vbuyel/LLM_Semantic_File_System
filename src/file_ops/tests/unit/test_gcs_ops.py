import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from adapters.gcs_ops import GCSOperations
from adapters.text_extractor import TextExtractorOperations


@pytest.fixture(autouse=True)
def mock_kafka():
    """Mock KafkaOperations used by GCS and TextExtractor."""
    mock_instance = MagicMock()
    mock_instance.send_command = AsyncMock()
    with (
        patch("adapters.gcs_ops.KafkaOperations") as mock_gcs_kafka,
        patch("adapters.text_extractor.KafkaOperations") as mock_te_kafka,
    ):
        mock_gcs_kafka.return_value = mock_instance
        mock_te_kafka.return_value = mock_instance
        yield mock_instance


@patch("adapters.gcs_ops.storage.Client")
def test_gcs_lazy_client_init(mock_client_class):
    """Verify that Client and Bucket are lazily initialized."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    gcs = GCSOperations(bucket_name="my-bucket")
    
    # Not initialized yet
    assert gcs._client is None
    assert gcs._bucket is None
    
    # Access client property
    assert gcs.client is mock_client
    mock_client_class.assert_called_once()
    
    # Access bucket property
    gcs.bucket
    mock_client.bucket.assert_called_once_with("my-bucket")


@pytest.mark.anyio
@patch("os.path.exists")
async def test_gcs_upload_file_path_validation(mock_exists):
    """Verify upload validation checks path existence and non-emptiness."""
    gcs = GCSOperations(bucket_name="my-bucket")

    # Empty source path
    with pytest.raises(ValueError) as exc:
        await gcs.upload_file(owner="guest", source_path="")
    assert "source_path cannot be empty" in str(exc.value)

    # Path doesn't exist
    mock_exists.return_value = False
    with pytest.raises(FileNotFoundError) as exc:
        await gcs.upload_file(owner="guest", source_path="non_existent.txt")
    assert "Source file not found" in str(exc.value)


@pytest.mark.anyio
@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=500)
@patch.object(TextExtractorOperations, "extract_text_from_file", return_value="Extracted text content")
async def test_gcs_upload_file_success(mock_extract, mock_getsize, mock_exists, mock_kafka):
    """Verify successful upload of file and sending Kafka event."""
    gcs = GCSOperations(bucket_name="my-bucket")
    
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    gcs._client = mock_client
    gcs._bucket = mock_bucket

    result = await gcs.upload_file(
        source_path="local/dir/test.txt",
        dest_name="remote_test.txt",
        mime_type="text/plain",
        owner="vlad",
    )

    assert result["file_id"] == "remote_test.txt"
    assert result["url"] == "gs://my-bucket/remote_test.txt"
    assert result["storage_type"] == "gcs"

    # Verify upload was called in executor
    mock_blob.upload_from_filename.assert_called_once_with(
        "local/dir/test.txt", content_type="text/plain"
    )
    
    # Verify text extraction called
    mock_extract.assert_called_once_with("local/dir/test.txt")
    
    # Verify chunked Kafka upload sent
    mock_kafka.send_command.assert_called_once()
    sent_data = mock_kafka.send_command.call_args[0][0]
    assert sent_data.action == "upload"
    assert sent_data.file_name == "remote_test.txt"
    assert sent_data.file_path == "root/"
    assert sent_data.text == "Extracted text content"
    assert sent_data.owner == "vlad"
    assert sent_data.storage_type == "gcs"
    assert sent_data.chunk_index == 0
    assert sent_data.file_size == 500


@pytest.mark.anyio
@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=500)
@patch.object(TextExtractorOperations, "extract_text_from_file", side_effect=Exception("Extraction Error"))
async def test_gcs_upload_file_extraction_failure(mock_extract, mock_getsize, mock_exists, mock_kafka):
    """Verify upload completes even if text extraction fails."""
    gcs = GCSOperations(bucket_name="my-bucket")
    
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    gcs._client = mock_client
    gcs._bucket = mock_bucket

    result = await gcs.upload_file(source_path="test.txt", owner="vlad")
    assert result["file_id"] == "test.txt"
    
    # Empty text after extraction failure is skipped by send_chunked_kafka
    mock_kafka.send_command.assert_not_called()


def test_gcs_list_files():
    """Verify list_files correctly formats blobs and folders."""
    gcs = GCSOperations(bucket_name="my-bucket")
    
    mock_client = MagicMock()
    gcs._client = mock_client
    
    # Setup mock blobs returned by list_blobs
    mock_blobs = MagicMock()
    mock_blobs.prefixes = ["root/folder1/", "root/folder2/"]
    
    blob1 = MagicMock()
    blob1.name = "root/file1.txt"
    blob1.size = 100
    blob1.updated.isoformat.return_value = "2026-05-18T10:00:00"
    
    blob2 = MagicMock()
    blob2.name = "root/file2.png"
    blob2.size = 200
    blob2.updated = None  # Handle no updated timestamp
    
    mock_blobs.__iter__.return_value = [blob1, blob2]
    mock_client.list_blobs.return_value = mock_blobs

    files = gcs.list_files(directory_path="/root")

    assert len(files) == 4
    # Check folder formatting
    assert files[0] == {
        "path": "root/folder1/",
        "name": "folder1",
        "isDirectory": True,
        "size": None,
        "modified": None,
    }
    # Check blob formatting
    assert files[2] == {
        "path": "root/file1.txt",
        "name": "file1.txt",
        "isDirectory": False,
        "size": 100,
        "modified": "2026-05-18T10:00:00",
    }
    assert files[3]["modified"] is None


def test_gcs_download_file():
    """Verify download_file behaves correctly."""
    gcs = GCSOperations(bucket_name="my-bucket")
    
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    gcs._bucket = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    # ValueError on empty path
    with pytest.raises(ValueError):
        gcs.download_file("")

    # FileNotFoundError if blob doesn't exist
    mock_blob.exists.return_value = False
    with pytest.raises(FileNotFoundError):
        gcs.download_file("missing.txt")

    # Success case
    mock_blob.exists.return_value = True
    mock_blob.content_type = "image/png"
    mock_blob.download_as_bytes.return_value = b"imagebytes"

    content, name, mime = gcs.download_file("path/to/my_image.png")
    assert content == b"imagebytes"
    assert name == "my_image.png"
    assert mime == "image/png"


@pytest.mark.anyio
async def test_gcs_delete_file_success(mock_kafka):
    """Verify delete_file deletes blob and notifies Kafka."""
    gcs = GCSOperations(bucket_name="my-bucket")
    
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    gcs._bucket = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_blob.exists.return_value = True

    await gcs.delete_file("folder/test_del.txt", owner="vlad")

    mock_blob.delete.assert_called_once()
    
    # Kafka notification checks
    mock_kafka.send_command.assert_called_once()
    sent_data = mock_kafka.send_command.call_args[0][0]
    assert sent_data.action == "delete"
    assert sent_data.file_name == "test_del.txt"
    assert sent_data.file_path == "root/"
    assert sent_data.owner == "vlad"
    assert sent_data.storage_type == "gcs"


@pytest.mark.anyio
async def test_gcs_rename_file_success(mock_kafka):
    """Verify rename_file renames blob and notifies Kafka."""
    gcs = GCSOperations(bucket_name="my-bucket")
    
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    gcs._bucket = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_blob.exists.return_value = True

    result = await gcs.rename_file("folder/old.txt", "new_name.txt", owner="vlad")

    mock_bucket.rename_blob.assert_called_once_with(mock_blob, "new_name.txt")
    assert result["file_id"] == "new_name.txt"
    assert result["url"] == "gs://my-bucket/new_name.txt"

    # Kafka notification checks
    mock_kafka.send_command.assert_called_once()
    sent_data = mock_kafka.send_command.call_args[0][0]
    assert sent_data.action == "rename"
    assert sent_data.file_name == "new_name.txt"
    assert sent_data.old_file_name == "old.txt"
    assert sent_data.owner == "vlad"
    assert sent_data.storage_type == "gcs"
