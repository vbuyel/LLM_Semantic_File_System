import os
import json
import uuid
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer

from src.file_ops.domain.domain import SendToKafka


logger = logging.getLogger(__name__)


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
        }


    async def start(self) -> None:
        """Start the producer. Call once at app startup."""
        await self._producer.start()


    async def stop(self) -> None:
        """Stop the producer. Call once at app shutdown."""
        await self._producer.stop()


    async def send_start_event(self, event: str, owner: Optional[str] = None) -> None:
        """Шаг 1: Отправить начальное событие в event_db."""
        try:
            event = {
                "owner": owner,
                "event": event,
            }
            await self._producer.send(self._event_db_topic, event)
        except Exception as e:
            logger.warning(f"Failed to send Kafka start event: {e}")


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
            logger.warning(f"Failed to send Kafka command: {e}")
