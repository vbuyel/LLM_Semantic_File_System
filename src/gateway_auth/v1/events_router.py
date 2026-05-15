import os, json, asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import httpx
import websockets
from src.gateway_auth.domain.settings import settings

event_router = APIRouter()
EVENT_DB_URL = os.getenv("EVENT_DB_URL", settings.EVENT_DB_URL)
EVENT_DB_WS = os.getenv("EVENT_DB_WS_URL", settings.EVENT_DB_WS_URL)
_clients: dict[str, list[WebSocket]] = {}

@event_router.get("/user/{owner}")
async def get_user_events(owner: str, limit: int = Query(100), offset: int = Query(0)):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{EVENT_DB_URL}/events/user/{owner}", params={"limit": limit, "offset": offset})
        return r.json()

@event_router.websocket("/ws/{owner}")
async def ws_handler(ws: WebSocket, owner: str):
    await ws.accept()
    _clients.setdefault(owner, []).append(ws)

    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{EVENT_DB_URL}/events/user/{owner}", params={"limit": 1})
            ev = r.json().get("events", [])
            if ev:
                await ws.send_json({"type": "events", "data": ev[0]})
    except Exception:
        pass

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _clients[owner] = [w for w in _clients.get(owner, []) if w is not ws]

async def relay_events():
    while True:
        try:
            async with websockets.connect(EVENT_DB_WS) as edb:
                print("[relay] Connected to event_db")
                async for raw in edb:
                    msg = json.loads(raw)
                    if msg.get("type") == "events" and msg.get("data"):
                        owner = msg["data"].get("owner")
                        for ws in _clients.get(owner, []):
                            try:
                                await ws.send_json(msg)
                            except Exception:
                                _clients[owner] = [w for w in _clients.get(owner, []) if w is not ws]
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
