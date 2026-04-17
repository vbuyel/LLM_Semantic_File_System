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


    def _get_most_relevant_text_from_files(self, encoded_query: List[float]) -> List[str]:
        return requests.get("http://localhost:9092/send/vector_db", params={"data": encoded_query})


    def do_search(self, query: RAGRequest) -> RAGResponse:
        encoded_query = self._encode_user_query(query.text)
        best_text_parts = self._get_most_relevant_text_from_files(encoded_query) # connect to kafka -> vector db
        return RAGResponse(text=best_text_parts)
