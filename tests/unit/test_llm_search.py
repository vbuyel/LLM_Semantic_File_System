"""
Unit tests for src.llm.adapters.web_search and src.llm.adapters.rag_search.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.llm.domain.domain import SearchResponse, RAGResponse

pytestmark = pytest.mark.unit


class TestWebSearch:
    def test_do_search_success(self):
        with patch("src.llm.adapters.web_search.DuckDuckGoSearchRun") as MockDDG:
            mock_session = MagicMock()
            mock_session.invoke.return_value = "Search results for AI"
            MockDDG.return_value = mock_session

            from src.llm.adapters.web_search import WebSearch
            ws = WebSearch()
            result = ws.do_search("artificial intelligence")
            assert isinstance(result, SearchResponse)
            assert "AI" in result.text

    def test_do_search_failure(self):
        with patch("src.llm.adapters.web_search.DuckDuckGoSearchRun") as MockDDG:
            mock_session = MagicMock()
            mock_session.invoke.side_effect = Exception("Network error")
            MockDDG.return_value = mock_session

            from src.llm.adapters.web_search import WebSearch
            ws = WebSearch()
            result = ws.do_search("query")
            assert "unavailable" in result.text.lower()


class TestRAGSearch:
    def test_do_search_success(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = MagicMock()
            mock_kafka.process.return_value = {"data": [{"text": "result"}]}
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = rs.do_search("test query")
            assert isinstance(result, RAGResponse)

    def test_do_search_failure(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = MagicMock()
            mock_kafka.process.side_effect = Exception("Kafka down")
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = rs.do_search("test")
            assert "unavailable" in result.text.lower()

    def test_do_search_string_response(self):
        with patch("src.llm.adapters.rag_search.Kafka") as MockKafka:
            mock_kafka = MagicMock()
            mock_kafka.process.return_value = "plain string result"
            MockKafka.return_value = mock_kafka

            from src.llm.adapters.rag_search import RAGSearch
            rs = RAGSearch()
            result = rs.do_search("query")
            assert result.text == "plain string result"
