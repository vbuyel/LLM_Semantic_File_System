from kafka import KafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import logging

from src.system.kafka.broker import BROKER_HOSTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class Message(BaseModel):
    data: dict


class TopicResponse(BaseModel):
    topic: str
    status: str
    message: str


def serialize(value):
    try:
        return json.dumps(value).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Message is not JSON-serializable: {e}")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=[*BROKER_HOSTS],
        value_serializer=serialize,
    )


async def send(topic: str, message: dict):
    producer = create_producer()
    try:
        producer.send(topic, value=message)
        producer.flush()
    finally:
        producer.close()


@app.post("/send/{topic}", response_model=TopicResponse)
async def send_message(topic: str, message: Message):
    try:
        await send(topic, message.data)
        return TopicResponse(topic=topic, status="sent", message="OK")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
