import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import uuid

from adapters.kafka import KafkaOperations
from domain.domain import SendToKafka


@pytest.fixture(autouse=True)
def reset_kafka_singleton():
    """Reset the singleton state of KafkaOperations between tests."""
    KafkaOperations._instance = None
    KafkaOperations._initialized = False


@patch("adapters.kafka.AIOKafkaProducer")
def test_kafka_singleton(mock_producer_class):
    """Verify that KafkaOperations is a singleton."""
    k1 = KafkaOperations()
    k2 = KafkaOperations()
    assert k1 is k2
    mock_producer_class.assert_called_once()


@patch("adapters.kafka.AIOKafkaProducer")
def test_kafka_init_config(mock_producer_class):
    """Verify initialization configuration from env vars."""
    with patch.dict("os.environ", {
        "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
        "REQUEST_TOPICS": "my.requests,other.topic",
        "REPLY_TOPIC": "my.replies",
        "EVENT_DB_TOPIC": "my_send_event",
    }):
        k = KafkaOperations()
        assert k._bootstrap_servers == "kafka:9092"
        assert k._request_topic == "my.requests"
        assert k._reply_topic == "my.replies"
        assert k._event_db_topic == "my_send_event"

        config = k._get_producer_config()
        assert config["bootstrap_servers"] == "kafka:9092"
        assert config["max_request_size"] == 50 * 1024 * 1024


@pytest.mark.anyio
@patch("adapters.kafka.AIOKafkaProducer")
@patch("aiokafka.admin.AIOKafkaAdminClient")
async def test_kafka_start(mock_admin_class, mock_producer_class):
    """Verify starting producer and creating missing topics."""
    mock_producer = AsyncMock()
    mock_producer_class.return_value = mock_producer

    mock_admin = AsyncMock()
    mock_admin.list_topics.return_value = []  # No topics exist
    mock_admin_class.return_value = mock_admin

    k = KafkaOperations()
    await k.start()

    mock_producer.start.assert_called_once()
    mock_admin.start.assert_called_once()
    mock_admin.list_topics.assert_called_once()
    mock_admin.create_topics.assert_called_once()
    mock_admin.close.assert_called_once()


@pytest.mark.anyio
@patch("adapters.kafka.AIOKafkaProducer")
async def test_kafka_stop(mock_producer_class):
    """Verify stopping the producer."""
    mock_producer = AsyncMock()
    mock_producer_class.return_value = mock_producer

    k = KafkaOperations()
    await k.stop()

    mock_producer.stop.assert_called_once()


@pytest.mark.anyio
@patch("adapters.kafka.AIOKafkaProducer")
async def test_send_event_success(mock_producer_class):
    """Verify send_event sends correctly formatted payload."""
    mock_producer = AsyncMock()
    mock_producer_class.return_value = mock_producer

    k = KafkaOperations()
    await k.send_event(event="Test Event", owner="vlad", correlation_id="corr-123")

    expected_msg = {
        "owner": "vlad",
        "ms_type": "file_ops",
        "event": "Test Event",
        "correlation_id": "corr-123",
    }
    mock_producer.send.assert_called_once_with(k._event_db_topic, expected_msg)


@pytest.mark.anyio
@patch("adapters.kafka.AIOKafkaProducer")
async def test_send_event_failure_no_raise(mock_producer_class):
    """Verify send_event logs error and does not raise exception on failure."""
    mock_producer = AsyncMock()
    mock_producer.send.side_effect = Exception("Kafka connection lost")
    mock_producer_class.return_value = mock_producer

    k = KafkaOperations()
    # Should not raise exception
    await k.send_event(event="Test Event")
    mock_producer.send.assert_called_once()


@pytest.mark.anyio
@patch("adapters.kafka.AIOKafkaProducer")
async def test_send_command_success(mock_producer_class):
    """Verify send_command parses data and sends payload to request topic."""
    mock_producer = AsyncMock()
    mock_producer_class.return_value = mock_producer

    k = KafkaOperations()
    command_data = SendToKafka(
        action="upload",
        file_name="file.txt",
        file_path="root/",
        text="Sample text",
        owner="vlad",
        storage_type="gcs",
        chunk_index=0,
        file_size=123,
    )

    await k.send_command(data=command_data, correlation_id="corr-999")

    mock_producer.send.assert_called_once()
    args, kwargs = mock_producer.send.call_args
    assert args[0] == k._request_topic
    sent_command = args[1]
    
    assert sent_command["correlation_id"] == "corr-999"
    assert sent_command["payload"]["action"] == "upload"
    assert sent_command["payload"]["file_name"] == "file.txt"
    assert sent_command["payload"]["text"] == "Sample text"
    assert sent_command["payload"]["owner"] == "vlad"
    assert sent_command["payload"]["file_size"] == 123
