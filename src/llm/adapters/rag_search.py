import json
from typing import Optional

from src.llm.domain.domain import RAGResponse
from src.llm.adapters.kafka import Kafka


class RAGSearch:
    def __init__(self):
        self._kafka = Kafka()
        self._started = False
        self.command = "search"
        self.event = "Found info in files"


    async def _ensure_started(self):
        if not self._started:
            await self._kafka._ensure_connections()
            self._started = True


    async def do_search(self, query: str, owner: str) -> RAGResponse:
        await self._ensure_started()
        try:
            data = await self._kafka.send_command(self.command, query, owner)
            if isinstance(data, str):
                return RAGResponse(text=data)

            records = data.get("data") if isinstance(data, dict) else data
            if not records:
                return RAGResponse(text="No relevant files found in the user's documents.")

            parts = []
            for i, record in enumerate(records, 1):
                file_name = record.get("file_name", "unknown")
                file_path = record.get("file_path", "unknown")
                text_chunk = record.get("text_chunk", "")
                parts.append(
                    f"--- Document {i}: {file_name} ---\n"
                    f"Path: {file_path}\n"
                    f"Content:\n{text_chunk}\n"
                )
            
            return RAGResponse(text="\n\n".join(parts))
        except Exception as exc:
            return RAGResponse(text=f"RAG unavailable: {exc}")
