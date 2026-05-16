"""
Run the server:
    uvicorn src.event_db.kafka_conn.main:app --port 8003
"""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from src.event_db.adapters.database import DataBase


load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
_db: Optional[DataBase] = None

_gateway_ws: Optional[WebSocket] = None
_kafka_task: asyncio.Task[None] | None = None
_kafka_healthy = False


def get_db():
    global _db
    if _db is None:
        _db = DataBase()
    return _db


async def _keep_consuming():
    """Run consumer loop with auto-restart on unexpected crashes."""
    global _kafka_task, _kafka_healthy
    retry_delay = 1.0
    while True:
        try:
            _kafka_task = asyncio.current_task()
            _kafka_healthy = False
            await process_requests()
            return
        except asyncio.CancelledError:
            _kafka_healthy = False
            return
        except Exception as exc:
            _kafka_healthy = False
            print(f"[ERROR] EventDB consumer crashed: {exc}. Restarting in {retry_delay:.0f}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _kafka_task
    _kafka_task = asyncio.create_task(_keep_consuming())
    try:
        yield
    finally:
        if _kafka_task:
            _kafka_task.cancel()
            try:
                await _kafka_task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/events/user/{owner}")
def get_user_events(owner: str, ms_type: str = Query(...), limit: int = Query(100), offset: int = Query(0)):
    """REST endpoint for fetching user events."""
    db = get_db()
    events = db.get_events_by_owner(owner, ms_type, limit=limit, offset=offset)
    return {"events": events}


@app.websocket("/ws/gateway")
async def gateway_ws(websocket: WebSocket):
    """WebSocket endpoint for gateway connection."""
    global _gateway_ws
    await websocket.accept()
    _gateway_ws = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _gateway_ws = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "event_db", "consumer_alive": _kafka_healthy}


async def process_requests():
    """Listen for Kafka requests, search DB, send replies."""
    global _kafka_healthy
    topics_str = os.getenv("REQUEST_TOPICS", "send_event")
    topics_list = [t.strip() for t in topics_str.split(",") if t.strip()]
    if not topics_list:
        topics_list = ["service.requests"]

    print(f"[DEBUG] EventDB listening on topics: {topics_list}")
    print(f"[DEBUG] Bootstrap servers: {_bootstrap_servers}")

    producer = AIOKafkaProducer(
        bootstrap_servers=_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    consumer = AIOKafkaConsumer(
        *topics_list,
        bootstrap_servers=_bootstrap_servers,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
    )
    
    await producer.start()
    await consumer.start()
    _kafka_healthy = True
    print("[DEBUG] EventDB Server is running")
    
    try:
        async for msg in consumer:
            try:
                data = msg.value
                print(f"[DEBUG] EventDB received Kafka message: {data}")

                owner = data.get("owner")
                ms_type = data.get("ms_type")
                event = data.get("event")
                
                print(f"[DEBUG] EventDB extracted owner='{owner}', ms_type='{ms_type}', event='{event}'")
                
                if not owner:
                    print(f"[WARNING] EventDB: Skipping event '{event}' - no owner provided")
                else:
                    print(f"[DEBUG] EventDB: Adding event to database for owner='{owner}', ms_type='{ms_type}', event='{event}'")
                    ev = get_db().add_event(owner=owner, ms_type=ms_type, event=event)
                    print(f"[DEBUG] EventDB: Event added successfully")
                    
                    if _gateway_ws:
                        print(f"[DEBUG] EventDB: Pushing event to gateway WebSocket")
                        try:
                            await _gateway_ws.send_json({
                                "type": "events",
                                "data": {
                                    **ev.model_dump(),
                                    "owner": owner,
                                }
                            })
                            print(f"[DEBUG] EventDB: Event pushed to gateway")
                        except Exception as e:
                            print(f"[ERROR] EventDB: Failed to push event to gateway: {e}")
                    else:
                        print(f"[DEBUG] EventDB: No gateway WebSocket connected, skipping push")
                
                print("[DEBUG] EventDB: Event processing completed")
            except Exception as e:
                print(f"[ERROR] EventDB: Error processing message: {e}")
    finally:
        _kafka_healthy = False
        await producer.stop()
        await consumer.stop()
