"""
Unit tests for src.gateway_auth.adapters.connection_manager.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.gateway_auth.adapters.connection_manager import ConnectionManager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_adds_ws(self, manager, mock_websocket):
        await manager.connect("user1", mock_websocket)
        mock_websocket.accept.assert_awaited_once()
        assert "user1" in manager.active_connections
        assert mock_websocket in manager.active_connections["user1"]

    @pytest.mark.asyncio
    async def test_connect_multiple_ws_same_owner(self, manager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect("user1", ws1)
        await manager.connect("user1", ws2)
        assert len(manager.active_connections["user1"]) == 2


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_removes_ws(self, manager, mock_websocket):
        await manager.connect("user1", mock_websocket)
        manager.disconnect("user1", mock_websocket)
        assert "user1" not in manager.active_connections

    def test_disconnect_unknown_owner(self, manager, mock_websocket):
        # Should not raise
        manager.disconnect("unknown", mock_websocket)

    @pytest.mark.asyncio
    async def test_disconnect_one_of_two(self, manager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect("user1", ws1)
        await manager.connect("user1", ws2)
        manager.disconnect("user1", ws1)
        assert len(manager.active_connections["user1"]) == 1
        assert ws2 in manager.active_connections["user1"]


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_to_owner(self, manager, mock_websocket):
        await manager.connect("user1", mock_websocket)
        await manager.broadcast_to_owner("user1", {"type": "test"})
        mock_websocket.send_json.assert_awaited_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self, manager):
        # Should not raise
        await manager.broadcast_to_owner("nobody", {"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_ws(self, manager):
        ws = AsyncMock()
        ws.send_json.side_effect = Exception("dead")
        await manager.connect("user1", ws)
        await manager.broadcast_to_owner("user1", {"type": "test"})
        # Dead ws should be removed
        assert "user1" not in manager.active_connections
