import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch, MagicMock
from adapters.kafka import Kafka


@pytest.fixture(autouse=True)
def reset_kafka_singleton():
    # Store old state
    old_instance = Kafka._instance
    old_initialized = Kafka._initialized
    old_producer = Kafka._producer
    old_consumer = Kafka._consumer

    # Reset singleton state before test
    Kafka._instance = None
    Kafka._initialized = False
    Kafka._producer = None
    Kafka._consumer = None

    yield

    # Restore singleton state after test
    Kafka._instance = old_instance
    Kafka._initialized = old_initialized
    Kafka._producer = old_producer
    Kafka._consumer = old_consumer


def test_kafka_singleton():
    k1 = Kafka()
    k2 = Kafka()
    assert k1 is k2
    assert k1._bootstrap_servers == ["localhost:9092"]
    assert k1._request_topic == "mock-request-topic"
    assert k1._reply_topic == "mock-reply-topic"
    assert k1._event_db_topic == "mock-event-topic"
    assert k1._timeout_sec == 5.0


@pytest.mark.asyncio
async def test_kafka_ensure_connections():
    with patch("adapters.kafka.AIOKafkaProducer") as mock_producer_class, \
         patch("adapters.kafka.AIOKafkaConsumer") as mock_consumer_class:
        
        mock_producer = mock_producer_class.return_value
        mock_producer.start = AsyncMock()
        
        mock_consumer = mock_consumer_class.return_value
        mock_consumer.start = AsyncMock()

        k = Kafka()
        await k._ensure_connections()

        # Check start was called on both
        mock_producer.start.assert_called_once()
        mock_consumer.start.assert_called_once()

        assert Kafka._producer is mock_producer
        assert Kafka._consumer is mock_consumer

        # Second call to ensure_connections should be a no-op
        await k._ensure_connections()
        mock_producer.start.assert_called_once()
        mock_consumer.start.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_send_event():
    with patch("adapters.kafka.AIOKafkaProducer") as mock_producer_class:
        mock_producer = mock_producer_class.return_value
        mock_producer.start = AsyncMock()
        mock_producer.send = AsyncMock()

        k = Kafka()
        # Mock connections as already established
        Kafka._producer = mock_producer

        await k.send_event("Test event", "user@gmail.com", "corr_123")

        mock_producer.send.assert_called_once_with(
            "mock-event-topic",
            {
                "owner": "user@gmail.com",
                "ms_type": "agent",
                "event": "Test event",
                "correlation_id": "corr_123"
            }
        )


@pytest.mark.asyncio
async def test_kafka_send_command_success():
    with patch("adapters.kafka.AIOKafkaProducer") as mock_producer_class, \
         patch("adapters.kafka.AIOKafkaConsumer") as mock_consumer_class, \
         patch("adapters.kafka.uuid.uuid4") as mock_uuid:
        
        mock_uuid.return_value = "my-corr-id-777"

        mock_producer = mock_producer_class.return_value
        mock_producer.send_and_wait = AsyncMock()

        mock_consumer = mock_consumer_class.return_value
        
        # Setup getmany to return matching correlation_id on the first call
        mock_message = MagicMock()
        mock_message.value = {
            "correlation_id": "my-corr-id-777",
            "data": "successful-rag-data"
        }
        
        # AIOKafkaConsumer.getmany returns a dict of {TopicPartition: [ConsumerRecord]}
        mock_consumer.getmany = AsyncMock(return_value={
            MagicMock(): [mock_message]
        })

        k = Kafka()
        Kafka._producer = mock_producer
        Kafka._consumer = mock_consumer

        result = await k.send_command("search", "python files", "john@gmail.com")

        assert result == "successful-rag-data"
        
        # Verify the published command structure
        mock_producer.send_and_wait.assert_called_once_with(
            "mock-request-topic",
            {
                "correlation_id": "my-corr-id-777",
                "reply_topic": "mock-reply-topic",
                "payload": {
                    "action": "search",
                    "text": "python files",
                    "limit": 3,
                    "owner": "john@gmail.com",
                }
            }
        )


@pytest.mark.asyncio
async def test_kafka_send_command_timeout():
    with patch("adapters.kafka.AIOKafkaProducer") as mock_producer_class, \
         patch("adapters.kafka.AIOKafkaConsumer") as mock_consumer_class:
        
        mock_producer = mock_producer_class.return_value
        mock_producer.send_and_wait = AsyncMock()

        mock_consumer = mock_consumer_class.return_value
        
        # Setup getmany to return only messages with non-matching correlation_id
        mock_message = MagicMock()
        mock_message.value = {
            "correlation_id": "different-corr-id",
            "data": "some-other-data"
        }
        mock_consumer.getmany = AsyncMock(return_value={
            MagicMock(): [mock_message]
        })

        k = Kafka()
        # Set a very low timeout to cause quick failure
        k._timeout_sec = 0.05
        Kafka._producer = mock_producer
        Kafka._consumer = mock_consumer

        with pytest.raises(TimeoutError) as exc_info:
            await k.send_command("search", "python files", "john@gmail.com")
        
        assert "Timeout waiting reply for correlation_id=" in str(exc_info.value)
