import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager, suppress
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None
_reply_consumer: AIOKafkaConsumer | None = None
_reply_task: asyncio.Task | None = None
_pending_requests: dict[str, asyncio.Future] = {}

REQUEST_TOPIC = os.getenv("REQUEST_TOPIC", "service.requests")
REPLY_TOPIC = os.getenv("REPLY_TOPIC", "service.replies")
REQUEST_TIMEOUT_SEC = float(os.getenv("REQUEST_TIMEOUT_SEC", "15"))


class Message(BaseModel):
    data: dict


class TopicResponse(BaseModel):
    correlation_id: str
    status: str
    data: dict[str, Any] | list[Any] | str | None


async def get_producer():
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=os.getenv("BROKER_HOSTS", "localhost:9092").split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
    return _producer


async def get_reply_consumer() -> AIOKafkaConsumer:
    global _reply_consumer
    if _reply_consumer is None:
        _reply_consumer = AIOKafkaConsumer(
            REPLY_TOPIC,
            bootstrap_servers=os.getenv("BROKER_HOSTS", "localhost:9092").split(","),
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id=os.getenv("SERVER1_REPLY_GROUP", "server1-reply-group"),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await _reply_consumer.start()
    return _reply_consumer


async def consume_replies() -> None:
    consumer = await get_reply_consumer()
    async for msg in consumer:
        payload = msg.value if isinstance(msg.value, dict) else {}
        correlation_id = payload.get("correlation_id")
        if not correlation_id:
            continue

        future = _pending_requests.pop(correlation_id, None)
        if future and not future.done():
            future.set_result(payload)


async def send(topic: str, message: dict) -> TopicResponse:
    producer = await get_producer()
    correlation_id = str(uuid.uuid4())
    response_future = asyncio.get_running_loop().create_future()
    _pending_requests[correlation_id] = response_future

    event = {
        "correlation_id": correlation_id,
        "reply_topic": REPLY_TOPIC,
        "payload": message,
    }
    await producer.send_and_wait(topic, event)

    try:
        response_event = await asyncio.wait_for(response_future, timeout=REQUEST_TIMEOUT_SEC)
    except TimeoutError as exc:
        _pending_requests.pop(correlation_id, None)
        raise HTTPException(
            status_code=504,
            detail=f"Timeout waiting for reply for correlation_id={correlation_id}",
        ) from exc

    return TopicResponse(
        correlation_id=correlation_id,
        status=response_event.get("status", "ok"),
        data=response_event.get("data"),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _reply_task
    await get_producer()
    await get_reply_consumer()
    _reply_task = asyncio.create_task(consume_replies())
    try:
        yield
    finally:
        if _reply_task is not None:
            _reply_task.cancel()
            with suppress(asyncio.CancelledError):
                await _reply_task
        if _reply_consumer is not None:
            await _reply_consumer.stop()
        if _producer is not None:
            await _producer.stop()


app = FastAPI(lifespan=lifespan)


@app.post("/request", response_model=TopicResponse)
async def send_request(message: Message):
    return await send(REQUEST_TOPIC, message.data)


@app.post("/send/{topic}", response_model=TopicResponse)
async def send_message(topic: str, message: Message):
    try:
        return await send(topic, message.data)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
