import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.llm.domain.domain import (
    RAGResponse,
)


class RAGSearch:
    def __init__(self):
        self._bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
        self._request_topic = os.getenv("REQUEST_TOPIC", "service.requests")
        self._reply_topic = os.getenv("REPLY_TOPIC", "service.replies")
        self._timeout_sec = float(os.getenv("RAG_KAFKA_TIMEOUT_SEC", "20"))
        self._executor = ThreadPoolExecutor(max_workers=1)


    async def _request_reply(self, query_text: str) -> Any:
        correlation_id = str(uuid.uuid4())
        consumer_group = f"rag-search-{correlation_id}"

        producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        consumer = AIOKafkaConsumer(
            self._reply_topic,
            bootstrap_servers=self._bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id=consumer_group,
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )

        try:
            # Start consumer first to avoid race where reply arrives before subscription.
            await consumer.start()
            await producer.start()

            event = {
                "correlation_id": correlation_id,
                "reply_topic": self._reply_topic,
                "payload": {
                    "action": "rag_search",
                    "text": query_text,
                },
            }
            await producer.send_and_wait(self._request_topic, event)

            deadline = asyncio.get_running_loop().time() + self._timeout_sec
            while True:
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError(
                        f"Timeout waiting reply for correlation_id={correlation_id}"
                    )

                batches = await consumer.getmany(timeout_ms=500, max_records=100)
                for _, messages in batches.items():
                    for message in messages:
                        value = message.value if isinstance(message.value, dict) else {}
                        if value.get("correlation_id") != correlation_id:
                            continue
                        return value.get("data")
        finally:
            await producer.stop()
            await consumer.stop()


    def do_search(self, query_text: str) -> RAGResponse:
        try:
            future = self._executor.submit(asyncio.run, self._request_reply(query_text))
            data = future.result(timeout=self._timeout_sec + 2)
            if isinstance(data, str):
                return RAGResponse(text=data)
            return RAGResponse(text=json.dumps(data, ensure_ascii=False, default=str))
        except Exception as exc:
            return RAGResponse(text=f"RAG unavailable: {exc}")
