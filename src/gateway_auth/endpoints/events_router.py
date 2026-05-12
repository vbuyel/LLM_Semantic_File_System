import os
from fastapi import APIRouter, WebSocketDisconnect, Query, HTTPException, status
import httpx

from src.gateway_auth.adapters.events_ws import manager


event_router = APIRouter(prefix="/events")

EVENT_DB_URL = os.getenv("EVENT_DB_URL", "http://localhost:8003")


@event_router.get("/user/{owner}")
async def get_user_events(owner: str, limit: int = Query(100), offset: int = Query(0)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{EVENT_DB_URL}/events/user/{owner}",
                params={"limit": limit, "offset": offset},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"event_db error: {e}")


@event_router.get("/")
async def get_latest_user_event(owner: str = Query(...)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{EVENT_DB_URL}/events/user/{owner}",
                params={"limit": 1, "offset": 0},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            events = data.get("events", [])
            if events:
                return {"event": events[0]}
            return {"event": None}
        except httpx.HTTPError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"event_db error: {e}")


@event_router.websocket("/ws/{owner}")
async def websocket_events(websocket, owner: str):
    await manager.connect(owner, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(owner, websocket)
