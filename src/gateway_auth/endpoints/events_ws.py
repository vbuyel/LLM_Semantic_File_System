import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional

from src.gateway_auth.adapters.event_db_adapter import get_event_db_adapter


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, owner: str, websocket: WebSocket):
        await websocket.accept()
        if owner not in self.active_connections:
            self.active_connections[owner] = []
        self.active_connections[owner].append(websocket)

    def disconnect(self, owner: str, websocket: WebSocket):
        if owner in self.active_connections:
            self.active_connections[owner] = [
                ws for ws in self.active_connections[owner] if ws != websocket
            ]
            if not self.active_connections[owner]:
                del self.active_connections[owner]

    async def broadcast_to_owner(self, owner: str, message: dict):
        if owner in self.active_connections:
            dead_ws = []
            for ws in self.active_connections[owner]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_ws.append(ws)
            for ws in dead_ws:
                self.disconnect(owner, ws)


manager = ConnectionManager()

_events_poll_task: Optional[asyncio.Task] = None
_last_event_ids: dict[str, int] = {}


async def poll_events():
    adapter = get_event_db_adapter()
    while True:
        for owner in list(manager.active_connections.keys()):
            try:
                events = adapter.get_events_by_owner(owner, limit=10, offset=0)
                if events:
                    last_id = _last_event_ids.get(owner)
                    new_events = [
                        e for e in events
                        if last_id is None or e["id"] > last_id
                    ]
                    if new_events:
                        _last_event_ids[owner] = events[0]["id"]
                        await manager.broadcast_to_owner(
                            owner,
                            {"type": "events", "data": new_events},
                        )
            except Exception:
                pass
        await asyncio.sleep(1)


def start_events_polling():
    global _events_poll_task
    if _events_poll_task is None:
        _events_poll_task = asyncio.create_task(poll_events())


def stop_events_polling():
    global _events_poll_task
    if _events_poll_task:
        _events_poll_task.cancel()
        _events_poll_task = None