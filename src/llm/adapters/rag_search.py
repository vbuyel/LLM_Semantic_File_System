import os
from typing import List
from sentence_transformers import SentenceTransformer
import requests

from src.llm.domain.domain import (
    RAGRequest,
    RAGResponse,
)


class RAGSearch:
    def __init__(self):
        self.model_embed = SentenceTransformer(os.getenv("MODEL_EMBED"))

    def _encode_user_query(self, query: str) -> List[float]:
        return self.model_embed.encode([query]).astype("float32")

    def _get_most_relevant_text_from_files(
        self, encoded_query: List[float]
    ) -> List[str]:
        response = requests.post(
            "http://localhost:8002/search",
            json={"embedding": encoded_query, "limit": 5},
            timeout=30,
        )
        response.raise_for_status()
        results = response.json()
        return [r.get("text", "") for r in results]

    def do_search(self, query: RAGRequest) -> RAGResponse:
        encoded_query = self._encode_user_query(query.text)
        best_text_parts = self._get_most_relevant_text_from_files(encoded_query)
        return RAGResponse(text=best_text_parts)
