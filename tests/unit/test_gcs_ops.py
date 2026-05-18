"""
Unit tests for adapters.gcs_ops (GCSOperations).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_kafka():
    with patch("src.file_ops.adapters.gcs_ops.KafkaOperations") as MockKafka:
        mock_instance = AsyncMock()
        MockKafka.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def gcs_ops(mock_kafka):
    with patch("src.file_ops.adapters.gcs_ops.storage") as mock_storage:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_storage.Client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        from src.file_ops.adapters.gcs_ops import GCSOperations
        ops = GCSOperations(bucket_name="test-bucket")
        ops._client = mock_client
        ops._bucket = mock_bucket
        yield ops, mock_bucket, mock_kafka


class TestGCSInit:
    def test_bucket_name(self, gcs_ops):
        ops, _, _ = gcs_ops
        assert ops.bucket_name == "test-bucket"


class TestGCSUpload:
    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, gcs_ops):
        ops, _, _ = gcs_ops
        with pytest.raises(FileNotFoundError):
            await ops.upload_file("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_upload_empty_path_raises(self, gcs_ops):
        ops, _, _ = gcs_ops
        with pytest.raises(ValueError, match="source_path cannot be empty"):
            await ops.upload_file("")


class TestGCSListFiles:
    def test_list_files_default_path(self, gcs_ops):
        ops, mock_bucket, _ = gcs_ops
        mock_blobs = MagicMock()
        mock_blobs.prefixes = ["folder1/"]
        mock_blobs.__iter__ = lambda self: iter([])
        ops.client.list_blobs.return_value = mock_blobs
        files = ops.list_files("/")
        assert len(files) == 1
        assert files[0]["isDirectory"] is True
        assert files[0]["name"] == "folder1"

    def test_list_files_with_files(self, gcs_ops):
        ops, _, _ = gcs_ops
        mock_blob = MagicMock()
        mock_blob.name = "folder/test.txt"
        mock_blob.size = 1024
        mock_blob.updated = None
        mock_blobs = MagicMock()
        mock_blobs.prefixes = []
        mock_blobs.__iter__ = lambda self: iter([mock_blob])
        ops.client.list_blobs.return_value = mock_blobs
        files = ops.list_files("/folder")
        assert len(files) == 1
        assert files[0]["name"] == "test.txt"
        assert files[0]["size"] == 1024


class TestGCSDownload:
    def test_download_empty_path_raises(self, gcs_ops):
        ops, _, _ = gcs_ops
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            ops.download_file("")

    def test_download_not_found(self, gcs_ops):
        ops, mock_bucket, _ = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        with pytest.raises(FileNotFoundError):
            ops.download_file("missing.txt")

    def test_download_success(self, gcs_ops):
        ops, mock_bucket, _ = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.content_type = "text/plain"
        mock_blob.download_as_bytes.return_value = b"hello"
        mock_bucket.blob.return_value = mock_blob
        content, name, mime = ops.download_file("test.txt")
        assert content == b"hello"
        assert name == "test.txt"
        assert mime == "text/plain"


class TestGCSDelete:
    @pytest.mark.asyncio
    async def test_delete_empty_path_raises(self, gcs_ops):
        ops, _, _ = gcs_ops
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            await ops.delete_file("")

    @pytest.mark.asyncio
    async def test_delete_not_found_raises(self, gcs_ops):
        ops, mock_bucket, _ = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        with pytest.raises(FileNotFoundError):
            await ops.delete_file("missing.txt")

    @pytest.mark.asyncio
    async def test_delete_file_exists_sends_kafka(self, gcs_ops):
        ops, mock_bucket, mock_kafka = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob

        await ops.delete_file("existing.txt")

        assert mock_kafka.send_command.called


class TestGCSRename:
    @pytest.mark.asyncio
    async def test_rename_empty_path_raises(self, gcs_ops):
        ops, _, _ = gcs_ops
        with pytest.raises(ValueError):
            await ops.rename_file("", "new.txt")

    @pytest.mark.asyncio
    async def test_rename_empty_name_raises(self, gcs_ops):
        ops, _, _ = gcs_ops
        with pytest.raises(ValueError):
            await ops.rename_file("old.txt", "")

    @pytest.mark.asyncio
    async def test_rename_not_found(self, gcs_ops):
        ops, mock_bucket, _ = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        with pytest.raises(FileNotFoundError):
            await ops.rename_file("missing.txt", "new.txt")

    @pytest.mark.asyncio
    async def test_rename_success(self, gcs_ops):
        ops, mock_bucket, mock_kafka = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        mock_bucket.rename_blob.return_value = MagicMock()

        result = await ops.rename_file("old_name.txt", "new_name.txt")

        assert result["file_id"] == "new_name.txt"
        assert result["storage_type"] == "gcs"
        assert mock_kafka.send_command.called


class TestGCSErrorPropagation:
    @pytest.mark.asyncio
    async def test_upload_kafka_failure_does_not_raise(self, gcs_ops):
        ops, mock_bucket, mock_kafka = gcs_ops
        mock_kafka.send_command.side_effect = Exception("Kafka down")

        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = await ops.upload_file(temp_path)
            assert result["file_id"]
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_delete_kafka_failure_still_raises_file_not_found(self, gcs_ops):
        ops, mock_bucket, mock_kafka = gcs_ops
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        mock_kafka.send_command.side_effect = Exception("Kafka down")

        with pytest.raises(FileNotFoundError):
            await ops.delete_file("nonexistent.txt")