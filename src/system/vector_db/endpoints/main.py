import asyncio
import json
import os
from sentence_transformers import SentenceTransformer
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from system.vector_db.adapters.database import DataBase


_embedding_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
_request_topic = os.getenv("REQUEST_TOPIC", "service.requests")
_reply_topic = os.getenv("REPLY_TOPIC", "service.replies")

db = DataBase()


async def process_requests():
    """Listen for Kafka requests, search DB, send replies."""
    producer = AIOKafkaProducer(bootstrap_servers=_bootstrap_servers)
    consumer = AIOKafkaConsumer(
        _request_topic,
        bootstrap_servers=_bootstrap_servers,
        group_id="vector-db-service",
        auto_offset_reset="latest",
    )
    
    await producer.start()
    await consumer.start()
    
    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                correlation_id = data["correlation_id"]
                payload = data["payload"]
                
                # Search
                embedding = _embedding_model.encode(payload["text"]).tolist()
                results = db.search_similar(embedding, limit=payload.get("limit", 3))
                
                # Reply
                reply = {"correlation_id": correlation_id, "data": results}
                await producer.send_and_wait(_reply_topic, json.dumps(reply).encode("utf-8"))
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(process_requests())
