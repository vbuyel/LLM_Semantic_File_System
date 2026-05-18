import logging
import os

from exa_py import AsyncExa

from adapters.kafka import Kafka
from domain.domain import SearchResponse


logger = logging.getLogger(__name__)


class WebSearch:
    def __init__(self):
        self._exa = AsyncExa(api_key=os.getenv("EXA_API_KEY"))
        self._kafka = Kafka()
        self._started = False
        self._start_event = "Searching in web..."


    async def _ensure_started(self):
        if not self._started:
            await self._kafka._ensure_connections()
            self._started = True


    async def do_search(self, query: str, owner: str, correlation_id: str) -> SearchResponse:
        await self._ensure_started()
        try:
            await self._kafka.send_event(self._start_event, owner, correlation_id)
            results = await self._exa.search(
                query,
                num_results=10,
                contents={"highlights": True},
            )
            return SearchResponse(text=self._format_results(results))
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return SearchResponse(text="Web search unavailable. Please try again later.")


    @staticmethod
    def _format_results(results) -> str:
        if not results or not results.results:
            return "No search results found."

        parts = []
        for i, r in enumerate(results.results, 1):
            parts.append(f"{i}. {r.title or 'Untitled'}")
            if r.url:
                parts.append(f"   URL: {r.url}")
            if r.highlights:
                for h in r.highlights:
                    parts.append(f"   {h}")
            if r.text and not r.highlights:
                parts.append(f"   {r.text[:500]}")
        return "\n".join(parts)
