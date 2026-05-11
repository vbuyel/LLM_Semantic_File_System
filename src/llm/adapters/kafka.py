import asyncio
import os
from typing import Optional
import uuid
import json
from concurrent.futures import ThreadPoolExecutor

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


class Kafka:
    def __init__(self):
        raw_broker_hosts = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._bootstrap_servers = [host.strip() for host in raw_broker_hosts.split(",") if host.strip()]

        self._request_topic = (
            os.getenv("REQUEST_TOPIC_RAG")
            or "service.requests"
        )
        self._reply_topic = (
            os.getenv("REPLY_TOPIC_RAG")
            or "service.replies"
        )
        self._event_db_topic = (
            os.getenv("EVENT_DB_TOPIC")
            or "send_event"
        )
        self._timeout_sec = float(os.getenv("RAG_KAFKA_TIMEOUT_SEC", "20"))

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        self._consumer = AIOKafkaConsumer(
            self._reply_topic,
            bootstrap_servers=self._bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )

        self._executor = ThreadPoolExecutor(max_workers=1)


    async def process(self, query_text: str, action: str, owner: Optional[str] = None):
        future = self._executor.submit(asyncio.run, self._send_to_kafka(query_text, action, owner))
        data = future.result(timeout=self._timeout_sec + 2)
        return data


    async def _send_to_kafka(self, query_text: str, action: str, owner: Optional[str] = None):
        correlation_id = str(uuid.uuid4())

        try:
            await self._consumer.start()
            await self._producer.start()

            command = {
                "correlation_id": correlation_id,
                "reply_topic": self._reply_topic,
                "payload": {
                    "text": query_text,
                    "limit": 3,
                },
            }
            
            # Send to event db file action
            event = {
                "owner": owner,
                "event": action,
            }
            await self._producer.send(self._event_db_topic, event)

            # Send to vector db to do action
            await self._producer.send_and_wait(self._request_topic, command)

            deadline = asyncio.get_running_loop().time() + self._timeout_sec
            while True:
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError(
                        f"Timeout waiting reply for correlation_id={correlation_id}"
                    )

                batches = await self._consumer.getmany(timeout_ms=500, max_records=100)
                for _, messages in batches.items():
                    for message in messages:
                        value = message.value if isinstance(message.value, dict) else {}
                        if value.get("correlation_id") != correlation_id:
                            continue
                        return value.get("data")
        finally:
            await self._producer.stop()
            await self._consumer.stop()
