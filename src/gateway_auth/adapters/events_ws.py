import asyncio
import json
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path
import websockets

from src.gateway_auth.adapters.connection_manager import ConnectionManager


load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

manager = ConnectionManager()

_eventdb_task: Optional[asyncio.Task] = None


async def relay_events_from_eventdb():
    eventdb_ws_url = os.getenv("EVENT_DB_WS_URL", "ws://localhost:8003/ws/gateway")
    
    while True:
        try:
            async with websockets.connect(eventdb_ws_url) as ws:
                print("[Gateway] Connected to event_db WebSocket")
                
                async for data in ws:
                    msg = json.loads(data)
                    
                    if msg.get("type") == "events" and msg.get("data"):
                        owner = msg["data"].get("owner")
                        if owner:
                            await manager.broadcast_to_owner(
                                owner,
                                {"type": "events", "data": msg["data"]}
                            )
        except Exception as e:
            print(f"[Gateway] EventDB WS error: {e}")
            await asyncio.sleep(5)


def start_eventdb_relay():
    global _eventdb_task
    if _eventdb_task is None:
        _eventdb_task = asyncio.create_task(relay_events_from_eventdb())


def stop_eventdb_relay():
    global _eventdb_task
    if _eventdb_task:
        _eventdb_task.cancel()
        _eventdb_task = None
