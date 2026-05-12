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
from src.vector_db.domain.domain import DeleteObject, RenameObject, UploadEvent, UploadObject

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")

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

    topics_str = os.getenv("REPLY_EVENT_TOPIC", "send_event")
    event_topics = [t.strip() for t in topics_str.split(",") if t.strip()]
    event_topic = event_topics[0] if event_topics else "send_event"

    print(f"[DEBUG] VectorDB listening on topics: {topics_list}")
    print(f"[DEBUG] VectorDB send events in topics: {event_topic}")
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
                correlation_id = data["correlation_id"]
                reply_topic = data["reply_topic"]
                payload = data["payload"]
                action = payload.get("action", "NOT FOUND")
                
                if action == "uploading":
                    action = "upload"
                elif action == "updating":
                    action = "update"

                event = {}
                event["owner"] = payload.get("owner")
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
                    event["event"] = "uploaded"
                    await producer.send(event_topic, event)
                elif action == "update":
                    print("File is updating (delete + upload)")
                    object_to_delete = DeleteObject(
                        path=payload.get("file_path", ""),
                        storage_type=payload.get("storage_type", ""),
                        owner=payload.get("owner")
                    )
                    get_db().delete_object(object_to_delete)
                    
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
                    event["event"] = "updated"
                    await producer.send(event_topic, event)
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
                    event["event"] = "deleted"
                    await producer.send(event_topic, event)
                elif action == "rename":
                    print("File is renaming now")
                    object_to_rename = RenameObject(
                        old_path=payload.get("file_path", ""),
                        new_path=payload.get("new_path", ""),
                        storage_type=payload.get("storage_type", ""),
                        owner=payload.get("owner")
                    )
                    result = get_db().rename_object(object_to_rename)

                    reply_message = {
                        "correlation_id": correlation_id,
                        "data": result.model_dump(mode="json"),
                    }
                    event["event"] = "renamed"
                    await producer.send(event_topic, event)
                elif action == "search":
                    embedding = get_embedding_model().encode(payload["text"]).tolist()
                    results = get_db().search_similar(embedding, limit=payload.get("limit", 3))
                    reply_message = {
                        "correlation_id": correlation_id,
                        "data": results.model_dump(mode="json"),
                    }

                    event["event"] = "found"
                    await producer.send(event_topic, event)
                else:
                    raise Exception(f"Action {action} is not supported in vector db")
                
                print("Vector DB operations are completed")
                await producer.send_and_wait(reply_topic, reply_message)
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(process_requests())
