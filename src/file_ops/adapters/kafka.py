import os
import json
import uuid
from typing import Optional

from aiokafka import AIOKafkaProducer

from src.file_ops.domain.domain import SendToKafka


class KafkaOperations:
    _instance = None
    _initialized = False


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        if self._initialized:
            return
        self._bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._request_topic = os.getenv("REQUEST_TOPICS", "service.requests").split(",")[0]
        self._reply_topic = os.getenv("REPLY_TOPIC", "service.replies")
        self._event_db_topic = os.getenv("EVENT_DB_TOPIC", "send_event")
        self._producer = AIOKafkaProducer(**self._get_producer_config())
        KafkaOperations._initialized = True


    def _get_producer_config(self) -> dict:
        return {
            "bootstrap_servers": self._bootstrap_servers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
            "max_request_size": 50 * 1024 * 1024,  # 50 MB
        }


    async def start(self) -> None:
        """Start the producer. Call once at app startup."""
        await self._producer.start()
        try:
            from aiokafka.admin import AIOKafkaAdminClient, NewTopic
            admin = AIOKafkaAdminClient(bootstrap_servers=self._bootstrap_servers)
            await admin.start()
            existing = await admin.list_topics()
            if self._event_db_topic not in existing:
                print(f"[DEBUG] Kafka: Creating topic '{self._event_db_topic}'")
                await admin.create_topics([NewTopic(self._event_db_topic, num_partitions=1, replication_factor=1)])
            await admin.close()
        except ImportError:
            print("[DEBUG] Kafka: aiokafka.admin not available, relying on auto-create")
        except Exception as e:
            print(f"[DEBUG] Kafka: Topic setup skipped ({e})")


    async def stop(self) -> None:
        """Stop the producer. Call once at app shutdown."""
        await self._producer.stop()


    async def send_event(self, event: str, owner: Optional[str] = None) -> None:
        """Шаг 1: Отправить начальное событие в event_db."""
        try:
            msg = {
                "owner": owner,
                "event": event,
            }
            print(f"[DEBUG] Kafka: sending event to topic='{self._event_db_topic}': {msg}")
            await self._producer.send_and_wait(self._event_db_topic, msg)
        except Exception as e:
            print(f"[ERROR] Failed to send Kafka event (topic={self._event_db_topic}): {e}")


    async def send_command(
        self,
        data: SendToKafka,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Шаг 2: Отправить команду в vector_db для обработки."""
        correlation_id = correlation_id or str(uuid.uuid4())
        try:
            command = {
                "correlation_id": correlation_id,
                "payload": {
                    "action": data.action,
                    "file_name": data.file_name,
                    "file_path": data.file_path,
                    "text": data.text,
                    "owner": data.owner,
                    "storage_type": data.storage_type,
                },
            }
            await self._producer.send_and_wait(self._request_topic, command)
        except Exception as e:
            print(f"[ERROR] Failed to send Kafka command (topic={self._request_topic}): {e}")
