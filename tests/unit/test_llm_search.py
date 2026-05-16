"""
Unit tests for src.llm.adapters.web_search and src.llm.adapters.rag_search.
"""
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.llm.domain.domain import SearchResponse, RAGResponse

# aiokafka is not installed in CI/test env — fake the module so imports work
sys.modules["aiokafka"] = MagicMock()
sys.modules["aiokafka"].AIOKafkaProducer = MagicMock()
sys.modules["aiokafka"].AIOKafkaConsumer = MagicMock()

pytestmark = pytest.mark.unit


class TestWebSearch:
    @pytest.mark.asyncio
    async def test_do_search_success(self):
        with patch("src.llm.adapters.web_search.AsyncExa") as MockExa, \
             patch("src.llm.adapters.web_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            MockKafka.return_value = mock_kafka

            mock_result = MagicMock()
            mock_result.title = "AI Overview"
            mock_result.url = "https://example.com/ai"
            mock_result.highlights = ["Artificial intelligence is transforming industries"]
            mock_result.text = None

            mock_search_result = MagicMock()
            mock_search_result.results = [mock_result]
            mock_exa = AsyncMock()
            mock_exa.search.return_value = mock_search_result
            MockExa.return_value = mock_exa

            from src.llm.adapters.web_search import WebSearch
            ws = WebSearch()
            result = await ws.do_search("artificial intelligence", "owner1")
            assert isinstance(result, SearchResponse)
            assert "AI" in result.text

    @pytest.mark.asyncio
    async def test_do_search_failure(self):
        with patch("src.llm.adapters.web_search.AsyncExa") as MockExa, \
             patch("src.llm.adapters.web_search.Kafka") as MockKafka:
            mock_kafka = AsyncMock()
            MockKafka.return_value = mock_kafka
            mock_exa = AsyncMock()
            mock_exa.search.side_effect = Exception("Network error")
            MockExa.return_value = mock_exa

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
