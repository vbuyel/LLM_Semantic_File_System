from langchain_community.tools import DuckDuckGoSearchRun
from src.llm.domain.domain import SearchResponse
import logging

logger = logging.getLogger(__name__)


class WebSearch:
    def __init__(self):
        self.session = DuckDuckGoSearchRun()


    def do_search(self, text: str) -> SearchResponse:
        try:
            result = self.session.invoke({"query": text})
            return SearchResponse(text=result)
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return SearchResponse(text="Web search unavailable. Please try again later.")
