from kafka import KafkaProducer
import json


def serialize(value):
    try:
        return json.dumps(value).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Message is not JSON-serializable: {e}")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=["localhost:9092"],
        value_serializer=serialize,
    )


async def send(topic: str, message: dict):
    producer = create_producer()
    try:
        producer.send(topic, value=message)
        producer.flush()
    finally:
        producer.close()


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(send("ai_agent", {"test": "message"}))
