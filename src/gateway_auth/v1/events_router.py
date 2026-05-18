import os, json, asyncio, uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import httpx
import websockets
from domain.settings import settings

event_router = APIRouter()
EVENT_DB_URL = os.getenv("EVENT_DB_URL", settings.EVENT_DB_URL)
EVENT_DB_WS = os.getenv("EVENT_DB_WS_URL", settings.EVENT_DB_WS_URL)
# Each entry: {"ws": WebSocket, "correlation_id": str}
_clients: dict[str, list[dict]] = {}


@event_router.get("/user/{owner}")
async def get_user_events(owner: str, ms_type: str = Query(...), limit: int = Query(100), offset: int = Query(0)):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{EVENT_DB_URL}/events/user/{owner}", params={"ms_type": ms_type, "limit": limit, "offset": offset})
        return r.json()


@event_router.websocket("/ws/{owner}")
async def ws_handler(ws: WebSocket, owner: str, correlation_id: str | None = Query(None)):
    await ws.accept()
    # Use correlation_id from query param if provided, otherwise generate new
    client_corr_id = correlation_id or str(uuid.uuid4())
    _clients.setdefault(owner, []).append({"ws": ws, "correlation_id": client_corr_id})

    try:
        # Send correlation_id to client for event filtering
        await ws.send_json({"type": "init", "correlation_id": client_corr_id})

        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{EVENT_DB_URL}/events/user/{owner}", params={"ms_type": "file_ops", "limit": 1})
                ev = r.json().get("events", [])
                if ev:
                    await ws.send_json({"type": "events", "data": ev[0]})
        except Exception:
            pass

        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if owner in _clients:
            _clients[owner] = [c for c in _clients.get(owner, []) if c["ws"] is not ws]
            if not _clients[owner]:
                del _clients[owner]


async def relay_events():
    while True:
        try:
            async with websockets.connect(EVENT_DB_WS) as edb:
                print("[relay] Connected to event_db")
                async for raw in edb:
                    msg = json.loads(raw)
                    data = msg.get("data", {})
                    if msg.get("type") == "events" and data:
                        owner = data.get("owner")
                        event_corr_id = data.get("correlation_id")
                        for client in _clients.get(owner, []):
                            ws = client["ws"]
                            client_corr_id = client["correlation_id"]
                            # Only relay if correlation_id matches (or event has no correlation_id for backward compat)
                            if event_corr_id is None or event_corr_id == client_corr_id:
                                try:
                                    await ws.send_json(msg)
                                except Exception:
                                    _clients[owner] = [c for c in _clients.get(owner, []) if c["ws"] is not ws]
        except Exception as e:
            print(f"[relay] Error: {e}")
            await asyncio.sleep(3)


_task: asyncio.Task | None = None


def start_relay():
    global _task
    if _task is None:
        _task = asyncio.create_task(relay_events())


def stop_relay():
    global _task
    if _task:
        _task.cancel()
        _task = None
