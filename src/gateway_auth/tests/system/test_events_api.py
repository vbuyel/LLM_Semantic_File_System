import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from v1.main import app
from v1.events_router import _clients, relay_events


@pytest.fixture
def client():
    # Make sure clients dict is clean before and after
    _clients.clear()
    yield TestClient(app)
    _clients.clear()


@patch("v1.events_router.httpx.AsyncClient.get")
def test_get_user_events(mock_get, client):
    """Verify GET /events/user/{owner} queries the event db correctly."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"events": [{"id": 1, "owner": "alice"}]}
    mock_get.return_value = mock_resp

    response = client.get(
        "/events/user/alice",
        params={"ms_type": "file_ops", "limit": 10, "offset": 2}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"events": [{"id": 1, "owner": "alice"}]}
    
    mock_get.assert_called_once()
    kwargs = mock_get.call_args[1]
    assert "events/user/alice" in mock_get.call_args[0][0]
    assert kwargs["params"] == {"ms_type": "file_ops", "limit": 10, "offset": 2}


@patch("v1.events_router.httpx.AsyncClient.get")
def test_websocket_flow_success(mock_get, client):
    """Verify WebSocket connection handles initialization, historic lookup, and safe cleanup."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"events": [{"event": "file_added", "path": "/a.txt"}]}
    mock_get.return_value = mock_resp

    with client.websocket_connect("/events/ws/alice?correlation_id=corr-alice-99") as ws:
        # Check initial registration in _clients dict
        assert "alice" in _clients
        assert len(_clients["alice"]) == 1
        assert _clients["alice"][0]["correlation_id"] == "corr-alice-99"

        # Receive "init" event
        init_msg = ws.receive_json()
        assert init_msg["type"] == "init"
        assert init_msg["correlation_id"] == "corr-alice-99"

        # Receive historic event queried from event db
        event_msg = ws.receive_json()
        assert event_msg["type"] == "events"
        assert event_msg["data"] == {"event": "file_added", "path": "/a.txt"}

    # After exiting block (disconnect), client must be cleaned up immediately
    assert "alice" not in _clients


@pytest.mark.anyio
@patch("v1.events_router.websockets.connect")
async def test_relay_events_distribution(mock_ws_connect):
    """Verify relay_events relays events only to matching clients and handles failures."""
    # Clean setup
    _clients.clear()

    # Create mock client websockets
    mock_ws1 = AsyncMock()  # Client 1: matches corr_id
    mock_ws2 = AsyncMock()  # Client 2: mismatched corr_id
    mock_ws3 = AsyncMock()  # Client 3: throws error on send

    _clients["alice"] = [
        {"ws": mock_ws1, "correlation_id": "corr-match"},
        {"ws": mock_ws2, "correlation_id": "corr-mismatch"},
        {"ws": mock_ws3, "correlation_id": "corr-match"},  # will fail on send
    ]

    # Setup mocked websockets.connect server generator yielding 1 message, then raising an error to break the infinite loop
    mock_db_conn = AsyncMock()
    
    # Event data received from central event db
    event_payload = {
        "type": "events",
        "data": {
            "owner": "alice",
            "correlation_id": "corr-match",
            "ms_type": "file_ops",
            "event": "file_deleted"
        }
    }
    
    # Create an async iterable mock for the `async for raw in edb:` loop
    class AsyncIterableMock:
        def __init__(self):
            self.delivered = False
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            if not self.delivered:
                self.delivered = True
                return json.dumps(event_payload)
            await asyncio.sleep(10)
            raise StopAsyncIteration("Stop connection after one message to end loop")

    mock_db_conn.__aiter__ = lambda self: AsyncIterableMock()
    
    # Setup websockets.connect context manager mock
    mock_connect_context = MagicMock()
    mock_connect_context.__aenter__ = AsyncMock(return_value=mock_db_conn)
    mock_connect_context.__aexit__ = AsyncMock(return_value=None)
    mock_ws_connect.return_value = mock_connect_context

    # Client 3 send should fail with an exception
    mock_ws3.send_json.side_effect = Exception("Closed connection")

    # Run relay_events briefly. Since we raise StopAsyncIteration, the loop will break or we can run it in a task and cancel.
    # Actually, websockets.connect iterator raising StopAsyncIteration will hit the `except Exception as e:` inside relay_events loop and retry, so it would infinite loop.
    # Let's make websockets.connect itself raise a cancellation/error after 1st cycle or terminate the task.
    
    # Let's run relay_events in a background asyncio task and cancel it after a very short sleep
    task = asyncio.create_task(relay_events())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify sends
    # 1. Matching client 1 should have received the JSON message
    mock_ws1.send_json.assert_called_once_with(event_payload)

    # 2. Mismatched client 2 should NOT have received the JSON message
    mock_ws2.send_json.assert_not_called()

    # 3. Client 3 should have failed, and then been removed from the clients list
    mock_ws3.send_json.assert_called_once_with(event_payload)
    
    # Check that Client 3 was removed, leaving Client 1 and Client 2
    registered_clients = _clients.get("alice", [])
    ws_list = [c["ws"] for c in registered_clients]
    assert mock_ws1 in ws_list
    assert mock_ws2 in ws_list
    assert mock_ws3 not in ws_list

    _clients.clear()
