import asyncio
import logging

from langchain_community.tools import DuckDuckGoSearchRun

from src.llm.adapters.kafka import Kafka
from src.llm.domain.domain import SearchResponse


logger = logging.getLogger(__name__)


class WebSearch:
    def __init__(self):
        self.session = DuckDuckGoSearchRun()
        self._kafka = Kafka()
        self._started = False
        self.event = "Searching in web..."


    async def _ensure_started(self):
        if not self._started:
            await self._kafka._ensure_connections()
            self._started = True


    async def do_search(self, query: str, owner: str) -> SearchResponse:
        await self._ensure_started()
        try:
            await self._kafka.send_event(self.event, owner)
            result = await asyncio.to_thread(self.session.invoke, {"query": query})
            return SearchResponse(text=result)
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return SearchResponse(text="Web search unavailable. Please try again later.")
