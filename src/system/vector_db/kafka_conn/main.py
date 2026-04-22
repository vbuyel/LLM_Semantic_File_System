import asyncio
import json
import os

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - for lightweight test environments
    SentenceTransformer = None

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except ImportError:  # pragma: no cover - for lightweight test environments
    AIOKafkaConsumer = None
    AIOKafkaProducer = None

from src.system.vector_db.adapters.database import DataBase


_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
_request_topic = os.getenv("REQUEST_TOPIC", "service.requests")

_embedding_model = None
_db = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed")
        _embedding_model = SentenceTransformer(
            os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
    return _embedding_model


def get_db():
    global _db
    if _db is None:
        _db = DataBase()
    return _db


async def process_requests():
    """Listen for Kafka requests, search DB, send replies."""
    if AIOKafkaProducer is None or AIOKafkaConsumer is None:
        raise RuntimeError("aiokafka is not installed")

    producer = AIOKafkaProducer(
        bootstrap_servers=_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    consumer = AIOKafkaConsumer(
        _request_topic,
        bootstrap_servers=_bootstrap_servers,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        group_id="vector-db-service",
        auto_offset_reset="latest",
    )
    
    await producer.start()
    await consumer.start()
    
    try:
        async for msg in consumer:
            try:
                # msg.value is already deserialized by value_deserializer.
                data = msg.value
                correlation_id = data["correlation_id"]
                reply_topic = data["reply_topic"]
                payload = data["payload"]
                
                # Search
                embedding = get_embedding_model().encode(payload["text"]).tolist()
                results = get_db().search_similar(embedding, limit=payload.get("limit", 3))
                
                # Reply
                reply_message = {
                    "correlation_id": correlation_id,
                    "data": results.model_dump(mode="json"),
                }
                await producer.send_and_wait(reply_topic, reply_message)
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(process_requests())
