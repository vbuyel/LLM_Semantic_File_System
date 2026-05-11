import json
from typing import Optional

from src.llm.domain.domain import RAGResponse
from src.llm.adapters.kafka import Kafka


class RAGSearch:
    def __init__(self):
        self._kafka_sender = Kafka()


    def do_search(self, query_text: str, owner: Optional[str] = None) -> RAGResponse:
        try:
            data = self._kafka_sender.process(query_text, "searching", owner)
            if isinstance(data, str):
                return RAGResponse(text=data)
            return RAGResponse(text=json.dumps(data, ensure_ascii=False, default=str))
        except Exception as exc:
            return RAGResponse(text=f"RAG unavailable: {exc}")
