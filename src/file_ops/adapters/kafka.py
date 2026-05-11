import os
import json
import uuid
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer

from file_ops.domain.domain import SendToKafka


logger = logging.getLogger(__name__)


class KafkaOperations:
    def __init__(self):
        self._bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._request_topic = os.getenv("REQUEST_TOPICS", "service.requests").split(",")[0]
        self._reply_topic = os.getenv("REPLY_TOPIC", "service.replies")
        self._event_db_topic = os.getenv("EVENT_DB_TOPIC", "send_event")
        self._producer = AIOKafkaProducer(**self._get_producer_config())


    def _get_producer_config(self) -> dict:
        return {
            "bootstrap_servers": self._bootstrap_servers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
        }

    async def send_start_event(self, action: str, owner: Optional[str] = None) -> None:
        """Шаг 1: Отправить начальное событие в event_db."""
        try:
            await self._producer.start()
            event = {
                "owner": owner,
                "event": action,
            }
            await self._producer.send(self._event_db_topic, event)
        except Exception as e:
            logger.warning(f"Failed to send Kafka start event: {e}")
        finally:
            await self._producer.stop()


    async def send_command(
        self,
        data: SendToKafka,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Шаг 2: Отправить команду в vector_db для обработки."""
        correlation_id = correlation_id or str(uuid.uuid4())
        try:
            await self._producer.start()
            command = {
                "correlation_id": correlation_id,
                "reply_topic": self._reply_topic,
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
        finally:
            await self._producer.stop()
