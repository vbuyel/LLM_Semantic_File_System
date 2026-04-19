import json
import os

import httpx

from src.llm.domain.domain import (
    RAGResponse,
)


class RAGSearch:
    def __init__(self):
        self._kafka_gateway_url = os.getenv("KAFKA_GATEWAY_URL", "http://localhost:8500")


    def do_search(self, query_text: str) -> RAGResponse:
        payload = {
            "action": "rag_search",
            "text": query_text,
        }

        try:
            response = httpx.post(
                f"{self._kafka_gateway_url}/request",
                json={"data": payload},
                timeout=20.0,
            )
            response.raise_for_status()
            body = response.json()
            data = body.get("data")
            if isinstance(data, str):
                return RAGResponse(text=data)
            return RAGResponse(text=json.dumps(data, ensure_ascii=False))
        except Exception as exc:
            return RAGResponse(text=f"RAG unavailable: {exc}")
