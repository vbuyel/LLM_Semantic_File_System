import asyncio
import os
from typing import Optional
import uuid
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


class Kafka:
    _instance = None
    _producer: Optional[AIOKafkaProducer] = None
    _consumer: Optional[AIOKafkaConsumer] = None
    _initialized = False
    _lock = asyncio.Lock()


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        if Kafka._initialized:
            return

        raw_broker_hosts = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._bootstrap_servers = [host.strip() for host in raw_broker_hosts.split(",") if host.strip()]

        self._request_topic = (
            os.getenv("REQUEST_TOPIC_RAG")
            or "service.requests"
        )
        self._reply_topic = (
            os.getenv("REPLY_TOPIC_RAG")
            or "reply_to_agent"
        )
        self._event_db_topic = (
            os.getenv("EVENT_DB_TOPIC")
            or "send_event"
        )
        self._timeout_sec = float(os.getenv("RAG_KAFKA_TIMEOUT_SEC", "30"))

        Kafka._initialized = True


    async def _ensure_connections(self):
        if Kafka._producer is not None and Kafka._consumer is not None:
            return

        async with Kafka._lock:
            if Kafka._producer is None:
                Kafka._producer = AIOKafkaProducer(
                    bootstrap_servers=self._bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                )
                await Kafka._producer.start()

            if Kafka._consumer is None:
                Kafka._consumer = AIOKafkaConsumer(
                    self._reply_topic,
                    bootstrap_servers=self._bootstrap_servers,
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=False,
                )
                await Kafka._consumer.start()


    async def send_event(self, event: str, owner: str, correlation_id: str):
        payload = {
            "owner": owner,
            "ms_type": "agent",
            "event": event,
            "correlation_id": correlation_id,
        }
        await Kafka._producer.send(self._event_db_topic, payload)


    async def send_command(self, command: str, query_text: str, owner: str):
        correlation_id = str(uuid.uuid4())

        command = {
            "correlation_id": correlation_id,
            "reply_topic": self._reply_topic,
            "payload": {
                "action": command,
                "text": query_text,
                "limit": 3,
                "owner": owner,
            },
        }

        await Kafka._producer.send_and_wait(self._request_topic, command)

        deadline = asyncio.get_running_loop().time() + self._timeout_sec
        while True:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(
                    f"Timeout waiting reply for correlation_id={correlation_id}"
                )

            batches = await Kafka._consumer.getmany(timeout_ms=500, max_records=100)
            for _, messages in batches.items():
                for message in messages:
                    value = message.value if isinstance(message.value, dict) else {}
                    if value.get("correlation_id") != correlation_id:
                        continue
                    return value.get("data")
