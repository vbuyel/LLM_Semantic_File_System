import json
import os
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


REQUEST_TOPIC = os.getenv("REQUEST_TOPIC", "service.requests")
REPLY_TOPIC = os.getenv("REPLY_TOPIC", "service.replies")


def create_consumer() -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        REQUEST_TOPIC,
        bootstrap_servers=os.getenv("BROKER_HOSTS", "localhost:9092").split(","),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        group_id=os.getenv("SERVER2_REQUEST_GROUP", "server2-request-group"),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )


def create_producer() -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=os.getenv("BROKER_HOSTS", "localhost:9092").split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def process_business_logic(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Точка бизнес-обработки на стороне server-2.
    Сейчас возвращает echo-ответ; здесь можно подключить доменную логику.
    """
    return {
        "received_payload": payload,
        "processed_by": "server-2",
    }


async def consume() -> None:
    consumer = create_consumer()
    producer = create_producer()
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            try:
                event = msg.value if isinstance(msg.value, dict) else {}
                correlation_id = event.get("correlation_id")
                payload = event.get("payload", {})
                reply_topic = event.get("reply_topic", REPLY_TOPIC)

                if not correlation_id:
                    raise ValueError("Missing correlation_id in request event")

                result = process_business_logic(payload)
                response_event = {
                    "correlation_id": correlation_id,
                    "status": "ok",
                    "data": result,
                }
                await producer.send_and_wait(reply_topic, response_event)
            except Exception as e:
                correlation_id = None
                if isinstance(msg.value, dict):
                    correlation_id = msg.value.get("correlation_id")
                if correlation_id:
                    error_event = {
                        "correlation_id": correlation_id,
                        "status": "error",
                        "data": {"message": str(e)},
                    }
                    await producer.send_and_wait(REPLY_TOPIC, error_event)
                print(f"Error processing message: {e}")
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(consume())
