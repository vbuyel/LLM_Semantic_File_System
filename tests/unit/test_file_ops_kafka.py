"""
Unit tests for src.file_ops.adapters.kafka (KafkaOperations).
"""
import pytest
from unittest.mock import patch, AsyncMock
from src.file_ops.domain.domain import SendToKafka

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_kafka_singleton():
    from src.file_ops.adapters.kafka import KafkaOperations
    KafkaOperations._instance = None
    KafkaOperations._initialized = False
    yield
    KafkaOperations._instance = None
    KafkaOperations._initialized = False


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    monkeypatch.setenv("REQUEST_TOPICS", "test.requests")
    monkeypatch.setenv("REPLY_TOPIC", "test.replies")
    monkeypatch.setenv("EVENT_DB_TOPIC", "test.events")


@pytest.fixture
def kafka_ops(mock_env):
    with patch("src.file_ops.adapters.kafka.AIOKafkaProducer") as MockProd:
        mock_producer = AsyncMock()
        MockProd.return_value = mock_producer
        from src.file_ops.adapters.kafka import KafkaOperations
        ops = KafkaOperations()
        ops._producer = mock_producer
        return ops


class TestKafkaOperations:
    def test_singleton(self, mock_env):
        with patch("src.file_ops.adapters.kafka.AIOKafkaProducer"):
            from src.file_ops.adapters.kafka import KafkaOperations
            assert KafkaOperations() is KafkaOperations()

    def test_config(self, kafka_ops):
        assert kafka_ops._request_topic == "test.requests"
        assert kafka_ops._event_db_topic == "test.events"

    @pytest.mark.asyncio
    async def test_start_stop(self, kafka_ops):
        await kafka_ops.start()
        kafka_ops._producer.start.assert_awaited_once()
        await kafka_ops.stop()
        kafka_ops._producer.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_start_event(self, kafka_ops):
        await kafka_ops.send_start_event(action="uploading", owner="u@t.com")
        kafka_ops._producer.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_command(self, kafka_ops):
        data = SendToKafka(action="upload", file_name="f.pdf", file_path="/tmp/f.pdf", text="c", owner="u", storage_type="gcs")
        await kafka_ops.send_command(data)
        kafka_ops._producer.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_command_exception_handled(self, kafka_ops):
        kafka_ops._producer.send.side_effect = Exception("fail")
        data = SendToKafka(action="upload", file_name="f", file_path="/p")
        await kafka_ops.send_command(data)  # should not raise
