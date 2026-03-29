import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm.agent_web_rag.adapters.web_search import WebSearch
from src.llm.agent_web_rag.domain.domain import SearchResponse


class TestWebSearch:
    @patch("src.llm.agent_web_rag.adapters.web_search.DuckDuckGoSearchRun")
    def test_web_search_initialization(self, mock_ddg):
        search = WebSearch()
        assert search.session is not None
        mock_ddg.assert_called_once()

    @patch("src.llm.agent_web_rag.adapters.web_search.DuckDuckGoSearchRun")
    def test_do_search_success(self, mock_ddg_cls):
        mock_session = Mock()
        mock_session.invoke.return_value = "Search results about Python"
        mock_ddg_cls.return_value = mock_session

        search = WebSearch()
        result = search.do_search("Python programming")

        assert isinstance(result, SearchResponse)
        assert result.text == "Search results about Python"

    @patch("src.llm.agent_web_rag.adapters.web_search.DuckDuckGoSearchRun")
    def test_do_search_returns_error_on_exception(self, mock_ddg_cls):
        mock_session = Mock()
        mock_session.invoke.side_effect = Exception("Network error")
        mock_ddg_cls.return_value = mock_session

        search = WebSearch()
        result = search.do_search("test query")

        assert isinstance(result, SearchResponse)
        assert "unavailable" in result.text.lower()

    @patch("src.llm.agent_web_rag.adapters.web_search.DuckDuckGoSearchRun")
    def test_do_search_with_empty_query(self, mock_ddg_cls):
        mock_session = Mock()
        mock_session.invoke.return_value = ""
        mock_ddg_cls.return_value = mock_session

        search = WebSearch()
        result = search.do_search("")

        assert isinstance(result, SearchResponse)

    @patch("src.llm.agent_web_rag.adapters.web_search.DuckDuckGoSearchRun")
    def test_do_search_with_special_characters(self, mock_ddg_cls):
        mock_session = Mock()
        mock_session.invoke.return_value = "Result with special chars: @#$%"
        mock_ddg_cls.return_value = mock_session

        search = WebSearch()
        result = search.do_search("test @#$% query")

        assert isinstance(result, SearchResponse)
