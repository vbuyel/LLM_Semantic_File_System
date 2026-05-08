"""
Run the server:
    python -m src.vector_db.kafka_conn.main
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except ImportError:
    AIOKafkaConsumer = None
    AIOKafkaProducer = None

from src.vector_db.adapters.database import DataBase
from src.vector_db.domain.domain import DeleteObject, ObjectDeleted, UploadObject

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
# _request_topics = os.getenv("REQUEST_TOPIC", "service.requests")

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

    topics_str = os.getenv("REQUEST_TOPICS", "service.requests")
    topics_list = [t.strip() for t in topics_str.split(",") if t.strip()]
    if not topics_list:
        topics_list = ["service.requests"]

    print(f"[DEBUG] VectorDB listening on topics: {topics_list}")
    print(f"[DEBUG] Bootstrap servers: {_bootstrap_servers}")

    producer = AIOKafkaProducer(
        bootstrap_servers=_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    consumer = AIOKafkaConsumer(
        *topics_list,
        bootstrap_servers=_bootstrap_servers,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        group_id="vector-db-service",
        auto_offset_reset="latest",
    )
    
    await producer.start()
    await consumer.start()
    print("Server is running")
    
    try:
        async for msg in consumer:
            try:
                data = msg.value
                correlation_id = data["correlation_id"]
                reply_topic = data["reply_topic"]
                payload = data["payload"]
                # action = payload.get("action", "")
                action = payload.get("action", "search")
                print(f"[DEBUG] Payload data: {payload}")
                
                if action == "upload":
                    print("File is starting to upload")
                    object_to_upload = UploadObject(
                        owner=payload.get("owner"),
                        file_name=payload.get("file_name", ""),
                        file_path=payload.get("file_path", ""),
                        text=payload.get("text", ""),
                    )
                    result = get_db().upload_object(object_to_upload)
                    reply_message = {
                        "correlation_id": correlation_id,
                        "data": result.model_dump(mode="json"),
                    }
                elif action == "delete":
                    print("File is deleting now")
                    object_to_delete = DeleteObject(
                        path=payload.get("file_path", ""),
                        storage_type=payload.get("storage_type", ""),
                        owner=payload.get("owner")
                    )
                    result = get_db().delete_object(object_to_delete)
                    reply_message = {
                        "correlation_id": correlation_id,
                        "data": result.model_dump(mode="json"),
                    }
                # elif action == "search":
                else:
                    embedding = get_embedding_model().encode(payload["text"]).tolist()
                    results = get_db().search_similar(embedding, limit=payload.get("limit", 3))
                    reply_message = {
                        "correlation_id": correlation_id,
                        "data": results.model_dump(mode="json"),
                    }
                
                print("Vector DB operations are completed")
                await producer.send_and_wait(reply_topic, reply_message)
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(process_requests())
