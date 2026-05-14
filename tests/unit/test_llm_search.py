"""
Unit tests for src.llm.adapters.web_search and src.llm.adapters.rag_search.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.llm.domain.domain import SearchResponse, RAGResponse

pytestmark = pytest.mark.unit


class TestWebSearch:
    @pytest.mark.asyncio
    async def test_do_search_success(self):
        with patch("src.llm.adapters.web_search.DuckDuckGoSearchRun") as MockDDG, \
             patch("src.llm.adapters.web_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            MockKafka.return_value = mock_kafka
            mock_session = MagicMock()
            mock_session.invoke.return_value = "Search results for AI"
            MockDDG.return_value = mock_session

            from src.llm.adapters.web_search import WebSearch
            ws = WebSearch()
            result = await ws.do_search("artificial intelligence", "owner1")
            assert isinstance(result, SearchResponse)
            assert "AI" in result.text

    @pytest.mark.asyncio
    async def test_do_search_failure(self):
        with patch("src.llm.adapters.web_search.DuckDuckGoSearchRun") as MockDDG, \
             patch("src.llm.adapters.web_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            MockKafka.return_value = mock_kafka
            mock_session = MagicMock()
            mock_session.invoke.side_effect = Exception("Network error")
            MockDDG.return_value = mock_session

            from src.llm.adapters.web_search import WebSearch
            ws = WebSearch()
            result = await ws.do_search("query", "owner1")
            assert "unavailable" in result.text.lower()


class TestRAGSearch:
    @pytest.mark.asyncio
    async def test_do_search_success(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            mock_kafka.send_command.return_value = {
                "data": [
                    {"file_name": "doc.txt", "file_path": "/docs/doc.txt", "text_chunk": "file content"}
                ]
            }
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = await rs.do_search("test query", "owner1")
            assert isinstance(result, RAGResponse)
            assert "doc.txt" in result.text

    @pytest.mark.asyncio
    async def test_do_search_failure(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            mock_kafka.send_command.side_effect = Exception("Kafka down")
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = await rs.do_search("test", "owner1")
            assert "unavailable" in result.text.lower()

    @pytest.mark.asyncio
    async def test_do_search_string_response(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            mock_kafka.send_command.return_value = "plain string result"
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = await rs.do_search("query", "owner1")
            assert result.text == "plain string result"

    @pytest.mark.asyncio
    async def test_do_search_no_records(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            mock_kafka.send_command.return_value = {"data": None}
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = await rs.do_search("query", "owner1")
            assert "No relevant files found" in result.text
