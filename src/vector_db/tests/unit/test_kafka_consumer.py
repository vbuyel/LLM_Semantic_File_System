import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from domain.domain import ObjectUploaded, ObjectDeleted, ObjectRenamed, RAGResults


@pytest.fixture
def mock_kafka_classes():
    # Force AIOKafkaProducer and AIOKafkaConsumer to be mocked classes
    mock_prod_cls = MagicMock()
    mock_cons_cls = MagicMock()
    
    with patch("v1.main.AIOKafkaProducer", mock_prod_cls), \
         patch("v1.main.AIOKafkaConsumer", mock_cons_cls):
        yield mock_prod_cls, mock_cons_cls


@pytest.mark.asyncio
async def test_run_consumer_loop_upload(mock_kafka_classes):
    mock_prod_cls, mock_cons_cls = mock_kafka_classes
    
    # Setup mock producer
    mock_producer = AsyncMock()
    mock_prod_cls.return_value = mock_producer
    
    # Setup mock consumer
    mock_consumer = AsyncMock()
    mock_cons_cls.return_value = mock_consumer
    
    # Create a mock upload message
    mock_msg = MagicMock()
    mock_msg.value = {
        "correlation_id": "corr-upload-123",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "upload",
            "owner": "owner@gmail.com",
            "file_name": "test.txt",
            "file_path": "docs/",
            "text": "test document text content",
            "file_size": 100,
            "chunk_index": 0
        }
    }
    
    # Feed list of mock messages to the consumer (AsyncMock will yield them)
    mock_consumer.__aiter__.return_value = [mock_msg]
    
    # Mock Database
    mock_db = MagicMock()
    mock_db.upload_object.return_value = ObjectUploaded(name="test.txt", chunks_added=3)
    
    with patch("v1.main.get_db", return_value=mock_db):
        from v1.main import _run_consumer_loop
        await _run_consumer_loop()
        
        # Verify database upload_object was called with correct parameters
        mock_db.upload_object.assert_called_once()
        called_arg = mock_db.upload_object.call_args[0][0]
        assert called_arg.owner == "owner@gmail.com"
        assert called_arg.file_name == "test.txt"
        assert called_arg.text == "test document text content"
        assert called_arg.file_size == 100
        
        # Verify reply was sent back to Kafka producer
        mock_producer.send_and_wait.assert_called_once_with(
            "reply-topic-abc",
            {
                "correlation_id": "corr-upload-123",
                "data": {"name": "test.txt", "chunks_added": 3}
            }
        )


@pytest.mark.asyncio
async def test_run_consumer_loop_delete(mock_kafka_classes):
    mock_prod_cls, mock_cons_cls = mock_kafka_classes
    
    mock_producer = AsyncMock()
    mock_prod_cls.return_value = mock_producer
    
    mock_consumer = AsyncMock()
    mock_cons_cls.return_value = mock_consumer
    
    mock_msg = MagicMock()
    mock_msg.value = {
        "correlation_id": "corr-delete-123",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "delete",
            "owner": "owner@gmail.com",
            "file_name": "test.txt",
            "file_path": "docs/",
            "storage_type": "local"
        }
    }
    mock_consumer.__aiter__.return_value = [mock_msg]
    
    mock_db = MagicMock()
    mock_db.delete_object.return_value = ObjectDeleted(name="test.txt", chunks_removed=3)
    
    with patch("v1.main.get_db", return_value=mock_db):
        from v1.main import _run_consumer_loop
        await _run_consumer_loop()
        
        mock_db.delete_object.assert_called_once()
        called_arg = mock_db.delete_object.call_args[0][0]
        assert called_arg.path == "docs/"
        assert called_arg.file_name == "test.txt"
        assert called_arg.storage_type == "local"
        assert called_arg.owner == "owner@gmail.com"
        
        mock_producer.send_and_wait.assert_called_once_with(
            "reply-topic-abc",
            {
                "correlation_id": "corr-delete-123",
                "data": {"name": "test.txt", "chunks_removed": 3}
            }
        )


@pytest.mark.asyncio
async def test_run_consumer_loop_rename(mock_kafka_classes):
    mock_prod_cls, mock_cons_cls = mock_kafka_classes
    
    mock_producer = AsyncMock()
    mock_prod_cls.return_value = mock_producer
    
    mock_consumer = AsyncMock()
    mock_cons_cls.return_value = mock_consumer
    
    mock_msg = MagicMock()
    mock_msg.value = {
        "correlation_id": "corr-rename-123",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "rename",
            "owner": "owner@gmail.com",
            "file_path": "docs/old.txt",
            "old_file_name": "old.txt",
            "new_path": "docs/new.txt",
            "file_name": "new.txt",
            "storage_type": "local"
        }
    }
    mock_consumer.__aiter__.return_value = [mock_msg]
    
    mock_db = MagicMock()
    mock_db.rename_object.return_value = ObjectRenamed(name="new.txt")
    
    with patch("v1.main.get_db", return_value=mock_db):
        from v1.main import _run_consumer_loop
        await _run_consumer_loop()
        
        mock_db.rename_object.assert_called_once()
        called_arg = mock_db.rename_object.call_args[0][0]
        assert called_arg.old_path == "docs/old.txt"
        assert called_arg.old_file_name == "old.txt"
        assert called_arg.new_path == "docs/new.txt"
        assert called_arg.new_name == "new.txt"
        assert called_arg.storage_type == "local"
        assert called_arg.owner == "owner@gmail.com"
        
        mock_producer.send_and_wait.assert_called_once_with(
            "reply-topic-abc",
            {
                "correlation_id": "corr-rename-123",
                "data": {"name": "new.txt"}
            }
        )


@pytest.mark.asyncio
async def test_run_consumer_loop_search(mock_kafka_classes):
    mock_prod_cls, mock_cons_cls = mock_kafka_classes
    
    mock_producer = AsyncMock()
    mock_prod_cls.return_value = mock_producer
    
    mock_consumer = AsyncMock()
    mock_cons_cls.return_value = mock_consumer
    
    mock_msg = MagicMock()
    mock_msg.value = {
        "correlation_id": "corr-search-123",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "search",
            "owner": "owner@gmail.com",
            "text": "test query text",
            "limit": 3
        }
    }
    mock_consumer.__aiter__.return_value = [mock_msg]
    
    mock_model = MagicMock()
    mock_emb = MagicMock()
    mock_emb.tolist.return_value = [0.1, 0.2, 0.3]
    mock_model.encode.return_value = mock_emb
    
    mock_db = MagicMock()
    mock_db.search_similar.return_value = RAGResults(data=[])
    
    with patch("v1.main.get_embedding_model", return_value=mock_model), \
         patch("v1.main.get_db", return_value=mock_db):
        from v1.main import _run_consumer_loop
        await _run_consumer_loop()
        
        mock_model.encode.assert_called_once_with("test query text")
        mock_db.search_similar.assert_called_once_with("owner@gmail.com", [0.1, 0.2, 0.3], limit=3)
        
        mock_producer.send_and_wait.assert_called_once_with(
            "reply-topic-abc",
            {
                "correlation_id": "corr-search-123",
                "data": {"data": []}
            }
        )


@pytest.mark.asyncio
async def test_run_consumer_loop_unsupported_action(mock_kafka_classes):
    mock_prod_cls, mock_cons_cls = mock_kafka_classes
    
    mock_producer = AsyncMock()
    mock_prod_cls.return_value = mock_producer
    
    mock_consumer = AsyncMock()
    mock_cons_cls.return_value = mock_consumer
    
    mock_msg = MagicMock()
    mock_msg.value = {
        "correlation_id": "corr-err-123",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "invalid_action_name"
        }
    }
    mock_consumer.__aiter__.return_value = [mock_msg]
    
    from v1.main import _run_consumer_loop
    # The loop should handle unsupported actions gracefully (print error) without throwing/crashing
    await _run_consumer_loop()
    
    # Verify no reply was sent since it errored before success
    mock_producer.send_and_wait.assert_not_called()


@pytest.mark.asyncio
async def test_run_consumer_loop_database_exception_handled_gracefully(mock_kafka_classes):
    mock_prod_cls, mock_cons_cls = mock_kafka_classes
    
    mock_producer = AsyncMock()
    mock_prod_cls.return_value = mock_producer
    
    mock_consumer = AsyncMock()
    mock_cons_cls.return_value = mock_consumer
    
    # We feed two messages. The first raises a DB exception; the second succeeds.
    # This verifies that the consumer loop does not break/exit upon an individual processing failure!
    msg_1 = MagicMock()
    msg_1.value = {
        "correlation_id": "corr-msg-1",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "upload",
            "owner": "owner@gmail.com",
            "file_name": "error.txt",
            "text": "causes crash"
        }
    }
    
    msg_2 = MagicMock()
    msg_2.value = {
        "correlation_id": "corr-msg-2",
        "reply_topic": "reply-topic-abc",
        "payload": {
            "action": "delete",
            "owner": "owner@gmail.com",
            "file_name": "success.txt"
        }
    }
    
    mock_consumer.__aiter__.return_value = [msg_1, msg_2]
    
    mock_db = MagicMock()
    # First call to upload_object raises exception
    mock_db.upload_object.side_effect = Exception("DB is locked!")
    mock_db.delete_object.return_value = ObjectDeleted(name="success.txt", chunks_removed=1)
    
    with patch("v1.main.get_db", return_value=mock_db):
        from v1.main import _run_consumer_loop
        await _run_consumer_loop()
        
        # Verify both database methods were called (loop did not exit after msg_1 failed)
        mock_db.upload_object.assert_called_once()
        mock_db.delete_object.assert_called_once()
        
        # Only reply for the second message should have been sent
        mock_producer.send_and_wait.assert_called_once_with(
            "reply-topic-abc",
            {
                "correlation_id": "corr-msg-2",
                "data": {"name": "success.txt", "chunks_removed": 1}
            }
        )
