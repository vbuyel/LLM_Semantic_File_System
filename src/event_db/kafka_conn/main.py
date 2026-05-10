"""
Run the server:
    python -m src.event_db.kafka_conn.main
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except ImportError:
    AIOKafkaConsumer = None
    AIOKafkaProducer = None

from src.event_db.adapters.database import DataBase


load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
_db = None


def get_db():
    global _db
    if _db is None:
        _db = DataBase()
    return _db


async def process_requests():
    """Listen for Kafka requests, search DB, send replies."""
    if AIOKafkaProducer is None or AIOKafkaConsumer is None:
        raise RuntimeError("aiokafka is not installed")

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
    print("Server is running")
    
    try:
        async for msg in consumer:
            try:
                data = msg.value

                # Add event into Event DataBase
                get_db().add_event(*data)
                
                print("Event DB operations are completed")
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(process_requests())
