from kafka import KafkaConsumer
import json
import httpx


TOPICS = [
    "ai_agent",
    "cloud_storage",
    "vector_db",
]

SERVERS_URL = {
    "ai_agent": "http://localhost:.../",
    "cloud_storage": "http://localhost:.../",
    "vector_db": "http://localhost:.../",
}


def create_consumer():
    return KafkaConsumer(
        *TOPICS,
        bootstrap_servers=["localhost:9092"],
        group_id="group_consumer",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )


async def forward_message(topic: str, payload: dict):
    url = SERVERS_URL.get(topic)
    if not url:
        raise ValueError(f"Unknown topic: {topic}")
    async with httpx.AsyncClient() as client:
        await client.post(f"{url}{topic}", json=payload, timeout=10.0)


async def consume():
    consumer = create_consumer()
    try:
        while True:
            messages = consumer.poll(timeout_ms=1000)
            for topic_partition, records in messages.items():
                topic = topic_partition.topic
                for record in records:
                    try:
                        await forward_message(topic, record.value)
                    except Exception as e:
                        print(f"Error processing message: {e}")
    finally:
        consumer.close()


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(consume())
