from aiokafka import AIOKafkaConsumer
import json
import httpx

from src.system.kafka.broker import TOPICS
from src.system.kafka.broker import BROKER_HOSTS


SERVERS_URL = {
    "web_rag": "http://localhost:9000/",
    "cloud_storage": "http://localhost:9001/",
    "vector_db": "http://localhost:9002/",
}


def create_consumer() -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=[*BROKER_HOSTS],
        group_id="group_consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )


async def forward_message(topic: str, payload: dict) -> None:
    url = SERVERS_URL.get(topic)
    if not url:
        raise ValueError(f"Unknown topic: {topic}")
    async with httpx.AsyncClient() as client:
        await client.post(f"{url}{topic}", json=payload, timeout=10.0)


async def consume() -> None:
    consumer = create_consumer()
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                await forward_message(msg.topic, msg.value)
            except Exception as e:
                print(f"Error processing message: {e}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(consume())
