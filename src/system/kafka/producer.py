from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import logging

from src.system.kafka.broker import BROKER_HOSTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
_producer = None


class Message(BaseModel):
    data: dict


class TopicResponse(BaseModel):
    topic: str
    status: str
    message: str


async def get_producer():
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=[*BROKER_HOSTS],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
    return _producer


async def send(topic: str, message: dict):
    producer = await get_producer()
    await producer.send_and_wait(topic, message)


@app.post("/send/{topic}", response_model=TopicResponse)
async def send_message(topic: str, message: Message):
    try:
        await send(topic, message.data)
        return TopicResponse(topic=topic, status="sent", message="OK")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
