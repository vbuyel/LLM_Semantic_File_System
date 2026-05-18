import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from adapters.kafka import Kafka


@pytest.fixture(autouse=True)
def reset_kafka_singleton():
    old_instance = Kafka._instance
    old_initialized = Kafka._initialized
    old_producer = Kafka._producer
    old_consumer = Kafka._consumer

    Kafka._instance = None
    Kafka._initialized = False
    Kafka._producer = None
    Kafka._consumer = None

    yield

    Kafka._instance = old_instance
    Kafka._initialized = old_initialized
    Kafka._producer = old_producer
    Kafka._consumer = old_consumer


@pytest.mark.asyncio
async def test_kafka_send_command_concurrency_race_condition():
    """
    This test demonstrates a major architectural bug in the Kafka adapter class:
    Since it is a singleton sharing a single `AIOKafkaConsumer` instance, concurrent 
    calls to `send_command` will compete in polling the consumer. 
    
    If Task A's loop polls a batch containing replies for BOTH Task A and Task B, 
    Task A will consume the batch, process its own message, and return. 
    However, Task B's reply message is permanently lost from the consumer stream.
    Task B will continue polling and eventually timeout, even though its reply 
    was successfully received by the client application.
    """
    with patch("adapters.kafka.AIOKafkaProducer") as mock_producer_class, \
         patch("adapters.kafka.AIOKafkaConsumer") as mock_consumer_class, \
         patch("adapters.kafka.uuid.uuid4") as mock_uuid:
        
        # We will trigger two concurrent send_command calls with separate correlation IDs
        corr_id_a = "corr-id-task-A"
        corr_id_b = "corr-id-task-B"
        mock_uuid.side_effect = [corr_id_a, corr_id_b]

        mock_producer = mock_producer_class.return_value
        mock_producer.send_and_wait = AsyncMock()

        mock_consumer = mock_consumer_class.return_value

        # We construct a single Kafka reply batch that contains responses for BOTH tasks
        msg_a = MagicMock()
        msg_a.value = {"correlation_id": corr_id_a, "data": "data-for-A"}
        msg_b = MagicMock()
        msg_b.value = {"correlation_id": corr_id_b, "data": "data-for-B"}

        full_batch = {
            MagicMock(): [msg_a, msg_b]
        }
        empty_batch = {}

        # Custom async poll mock that simulates a real broker poll delay.
        # This allows the asyncio event loop clock to advance, leading to a clean TimeoutError.
        call_count = 0
        async def mock_getmany(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            my_count = call_count  # Capture synchronously before yielding control via sleep
            await asyncio.sleep(0.05)  # Simulate a 50ms network poll wait
            if my_count == 1:
                return full_batch
            return empty_batch

        mock_consumer.getmany = mock_getmany

        k = Kafka()
        k._timeout_sec = 0.15  # Low timeout so test is fast
        Kafka._producer = mock_producer
        Kafka._consumer = mock_consumer

        # Run both commands concurrently using asyncio.gather
        # One of these tasks will capture the full batch first.
        # It will extract its message and return successfully.
        # The other task will be left with empty batches and will time out.
        results = await asyncio.gather(
            k.send_command("search", "query A", "user@gmail.com"),
            k.send_command("search", "query B", "user@gmail.com"),
            return_exceptions=True
        )

        # One task succeeded and returned its data
        succeeded_results = [r for r in results if isinstance(r, str)]
        # The other task timed out and raised a TimeoutError
        failed_results = [r for r in results if isinstance(r, TimeoutError)]

        # Verify the bug:
        assert len(succeeded_results) == 1, "Exactly one concurrent command should succeed"
        assert len(failed_results) == 1, "Exactly one concurrent command should fail with a TimeoutError due to shared consumer race condition"
        
        # Succeeded result matches one of our expected replies
        assert succeeded_results[0] in ("data-for-A", "data-for-B")
        
        # Failed result is indeed a TimeoutError
        assert "Timeout waiting reply for correlation_id=" in str(failed_results[0])
        print("\n[BUG VERIFIED] Successfully reproduced and tested the concurrent shared-consumer race condition!")
