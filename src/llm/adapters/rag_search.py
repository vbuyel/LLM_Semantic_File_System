import os
from typing import List
from sentence_transformers import SentenceTransformer
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json

from src.llm.domain.domain import (
    RAGRequest,
    RAGResponse,
)


class RAGSearch:
    def __init__(self):
        self._model_embed = SentenceTransformer(os.getenv("MODEL_EMBED"))

        self._producer = AIOKafkaProducer(
            bootstrap_servers=[os.getenv("BROKER_HOSTS").split(",")],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        ).start()
        self._consumer = AIOKafkaConsumer(
            os.getenv("TOPICS_FOR_RAG_CONSUMER").split(","),
            bootstrap_servers=os.getenv("BROKER_HOSTS").split(","),
            group_id="ai",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        ).start()


    def _encode_user_query(self, query: str) -> List[float]:
        return self._model_embed.encode([query]).astype("float32")


    def _get_ids_for_text(self, encoded_query: List[float]) -> List[str]:
        self._producer.send_and_wait(
            os.getenv("TOPIC_GET_TEXT_IDS"),
            {"embedding": encoded_query, "limit": 5}
        )
        response = []
        for msg in self._consumer:
            response.append(msg.get("ids"))
        return response


    def _get_text_from_ids(self, ids: List[int]) -> List[str]:
        self._producer.send_and_wait(
            os.getenv("TOPIC_SEARCH_TEXT_BY_IDS"),
            {"ids": ids}
        )
        response = []
        for msg in self._consumer:
            response.append(msg.get("ids"))
        return response


    def do_search(self, query: RAGRequest) -> RAGResponse:
        encoded_query = self._encode_user_query(query.text)
        text_ids = self._get_ids_for_text(encoded_query)
        founded_text = self._get_text_from_ids(text_ids)
        return RAGResponse(text=founded_text)
