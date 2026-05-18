import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from v1.main import process_requests, get_db
import v1.main as main_module
from domain.events import EventItem


class MockMessage:
    def __init__(self, value):
        self.value = value


class MockConsumer:
    def __init__(self, messages):
        self.messages = messages
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.messages:
            raise StopAsyncIteration
        return self.messages.pop(0)


class MockProducer:
    def __init__(self):
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True


@pytest.mark.anyio
async def test_process_requests_success():
    """Verify that valid Kafka messages are processed, stored to DB, and WebSocket notifications are sent."""
    # 1. Prepare mock messages
    messages = [
        MockMessage({
            "owner": "vlad",
            "ms_type": "user_action",
            "event": "file_uploaded",
            "correlation_id": "corr-100"
        })
    ]

    # 2. Mock DB, Kafka Producer/Consumer, and WebSocket
    mock_db = MagicMock()
    mock_event = EventItem(ms_type="user_action", event="file_uploaded", correlation_id="corr-100")
    mock_db.add_event.return_value = mock_event

    mock_ws = AsyncMock()

    consumer = MockConsumer(messages)
    producer = MockProducer()

    # 3. Patch and run
    with patch("v1.main.AIOKafkaConsumer", return_value=consumer), \
         patch("v1.main.AIOKafkaProducer", return_value=producer), \
         patch("v1.main.get_db", return_value=mock_db), \
         patch("v1.main._gateway_ws", mock_ws):

        await process_requests()

        # Check DB call
        mock_db.add_event.assert_called_once_with(
            owner="vlad",
            ms_type="user_action",
            event="file_uploaded",
            correlation_id="corr-100"
        )

        # Check WS push
        mock_ws.send_json.assert_called_once_with({
            "type": "events",
            "data": {
                "ms_type": "user_action",
                "event": "file_uploaded",
                "correlation_id": "corr-100",
                "owner": "vlad"
            }
        })

        # Check consumer state clean up
        assert not main_module._kafka_healthy
        assert consumer.started and consumer.stopped
        assert producer.started and producer.stopped


@pytest.mark.anyio
async def test_process_requests_missing_owner():
    """Verify that messages without an owner are skipped and NOT written to the database."""
    messages = [
        MockMessage({
            "ms_type": "user_action",
            "event": "file_uploaded"
        })
    ]

    mock_db = MagicMock()
    consumer = MockConsumer(messages)
    producer = MockProducer()

    with patch("v1.main.AIOKafkaConsumer", return_value=consumer), \
         patch("v1.main.AIOKafkaProducer", return_value=producer), \
         patch("v1.main.get_db", return_value=mock_db):

        await process_requests()

        mock_db.add_event.assert_not_called()


@pytest.mark.anyio
async def test_process_requests_exception_handling():
    """Verify that an exception processing one message (e.g. malformed payload) does not crash the loop."""
    messages = [
        # First message is completely invalid (not a dict, calling .get raises AttributeError)
        MockMessage(["invalid_list"]),
        # Second message is valid
        MockMessage({
            "owner": "vlad",
            "ms_type": "info",
            "event": "login",
            "correlation_id": "corr-2"
        })
    ]

    mock_db = MagicMock()
    mock_event = EventItem(ms_type="info", event="login", correlation_id="corr-2")
    mock_db.add_event.return_value = mock_event

    consumer = MockConsumer(messages)
    producer = MockProducer()

    with patch("v1.main.AIOKafkaConsumer", return_value=consumer), \
         patch("v1.main.AIOKafkaProducer", return_value=producer), \
         patch("v1.main.get_db", return_value=mock_db):

        # Should run through and complete, not raise AttributeError
        await process_requests()

        # Database should still have been called for the second (valid) message
        mock_db.add_event.assert_called_once_with(
            owner="vlad",
            ms_type="info",
            event="login",
            correlation_id="corr-2"
        )


@pytest.mark.anyio
async def test_process_requests_websocket_exception():
    """Verify that a failing WebSocket connection does not crash the consumer loop."""
    messages = [
        MockMessage({
            "owner": "vlad",
            "ms_type": "info",
            "event": "login",
            "correlation_id": "corr-3"
        })
    ]

    mock_db = MagicMock()
    mock_event = EventItem(ms_type="info", event="login", correlation_id="corr-3")
    mock_db.add_event.return_value = mock_event

    # Mock WebSocket that raises exception on send
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = Exception("WebSocket disconnected")

    consumer = MockConsumer(messages)
    producer = MockProducer()

    with patch("v1.main.AIOKafkaConsumer", return_value=consumer), \
         patch("v1.main.AIOKafkaProducer", return_value=producer), \
         patch("v1.main.get_db", return_value=mock_db), \
         patch("v1.main._gateway_ws", mock_ws):

        # Should finish successfully without raising the WebSocket exception
        await process_requests()

        # DB write should have occurred
        mock_db.add_event.assert_called_once()
        mock_ws.send_json.assert_called_once()
