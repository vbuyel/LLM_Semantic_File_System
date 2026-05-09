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
        self._producer = AIOKafkaProducer(**self._get_producer_config())


    def _get_producer_config(self) -> dict:
        return {
            "bootstrap_servers": self._bootstrap_servers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
        }

    async def _send_event(
        self,
        action: str,
        owner: Optional[str] = None,
    ) -> None:
        try:
            event = {
                "owner": owner,
                "event": action,
            }
            await self._producer.send(self._reply_topic, event)
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")


    async def _send_command(
        self,
        payload: dict,
        correlation_id: Optional[str] = None,
    ) -> None:
        try:
            command = {
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "reply_topic": self._reply_topic,
                "payload": payload,
            }
            await self._producer.send_and_wait(self._request_topic, command)
        except Exception as e:
            logger.warning(f"Failed to send Kafka command: {e}")


    async def send_to_kafka(self, data: SendToKafka) -> None:
        correlation_id = str(uuid.uuid4())

        try:
            await self._producer.start()
            await self._send_event(data.action, data.owner)
            await self._send_command(*data, correlation_id)
        finally:
            await self._producer.stop()
