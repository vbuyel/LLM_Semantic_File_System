"""
Unit tests for src.file_ops.adapters.kafka (KafkaOperations).
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

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
        assert kafka_ops._reply_topic == "test.replies"

    @pytest.mark.asyncio
    async def test_start_stop(self, kafka_ops):
        await kafka_ops.start()
        kafka_ops._producer.start.assert_awaited_once()
        await kafka_ops.stop()
        kafka_ops._producer.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_event(self, kafka_ops):
        await kafka_ops.send_event(event="Test event", owner="test@test.com")
        kafka_ops._producer.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_command(self, kafka_ops):
        from src.file_ops.domain.domain import SendToKafka
        data = SendToKafka(action="upload", file_name="f.pdf", file_path="/tmp/f.pdf", text="c", owner="u", storage_type="gcs")
        await kafka_ops.send_command(data)
        kafka_ops._producer.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_command_exception_handled(self, kafka_ops):
        kafka_ops._producer.send.side_effect = Exception("fail")
        from src.file_ops.domain.domain import SendToKafka
        data = SendToKafka(action="upload", file_name="f", file_path="/p")
        await kafka_ops.send_command(data)

    @pytest.mark.asyncio
    async def test_send_command_generates_correlation_id(self, kafka_ops):
        from src.file_ops.domain.domain import SendToKafka
        data = SendToKafka(action="upload", file_name="f.pdf", file_path="/tmp/f.pdf")
        await kafka_ops.send_command(data)
        call_args = kafka_ops._producer.send.call_args
        message = call_args[0][1]
        assert "correlation_id" in message
        assert len(message["correlation_id"]) > 0

    @pytest.mark.asyncio
    async def test_send_command_accepts_custom_correlation_id(self, kafka_ops):
        from src.file_ops.domain.domain import SendToKafka
        data = SendToKafka(action="upload", file_name="f.pdf", file_path="/tmp/f.pdf")
        custom_id = "custom-correlation-id-123"
        await kafka_ops.send_command(data, correlation_id=custom_id)
        call_args = kafka_ops._producer.send.call_args
        message = call_args[0][1]
        assert message["correlation_id"] == custom_id

    @pytest.mark.asyncio
    async def test_send_event_with_correlation_id(self, kafka_ops):
        correlation_id = "corr-123"
        await kafka_ops.send_event(event="Test", owner="user@test.com", correlation_id=correlation_id)
        call_args = kafka_ops._producer.send.call_args
        _, message = call_args[0]
        assert message["correlation_id"] == correlation_id

    @pytest.mark.asyncio
    async def test_send_event_null_owner(self, kafka_ops):
        await kafka_ops.send_event(event="Test event", owner=None)
        kafka_ops._producer.send.assert_awaited_once()

    def test_get_producer_config(self, kafka_ops):
        config = kafka_ops._get_producer_config()
        assert "bootstrap_servers" in config
        assert "value_serializer" in config
        assert config["max_request_size"] == 50 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_start_creates_topic_on_event_db(self, kafka_ops):
        with patch("src.file_ops.adapters.kafka.AIOKafkaAdminClient") as MockAdmin:
            mock_admin = AsyncMock()
            MockAdmin.return_value = mock_admin
            mock_admin.list_topics.return_value = []
            await kafka_ops.start()
            mock_admin.create_topics.assert_awaited()


class TestKafkaErrorScenarios:
    @pytest.mark.asyncio
    async def test_start_admin_error_handled(self, kafka_ops):
        with patch("src.file_ops.adapters.kafka.AIOKafkaAdminClient") as MockAdmin:
            mock_admin = AsyncMock()
            mock_admin.start.side_effect = Exception("Admin error")
            MockAdmin.return_value = mock_admin
            await kafka_ops.start()
            await kafka_ops.stop()

    @pytest.mark.asyncio
    async def test_send_event_swallows_exception(self, kafka_ops):
        kafka_ops._producer.send.side_effect = Exception("Connection lost")
        await kafka_ops.send_event(event="test", owner="test@test.com")

    @pytest.mark.asyncio
    async def test_multiple_topics_from_env(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        monkeypatch.setenv("REQUEST_TOPICS", "topic1,topic2,topic3")
        monkeypatch.setenv("REPLY_TOPIC", "test.replies")
        monkeypatch.setenv("EVENT_DB_TOPIC", "test.events")

        with patch("src.file_ops.adapters.kafka.AIOKafkaProducer"):
            from src.file_ops.adapters.kafka import KafkaOperations
            ops = KafkaOperations()
            assert ops._request_topic == "topic1"