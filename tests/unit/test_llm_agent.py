"""
Unit tests for src.llm.adapters.agent (AgentResearcher).
"""
import pytest
from unittest.mock import patch, MagicMock
from src.llm.domain.domain import SearchRequest, SearchResponse

pytestmark = pytest.mark.unit


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MODEL", "test-model")
    with patch("src.llm.adapters.agent.OpenAI") as MockOpenAI, \
         patch("src.llm.adapters.agent.RAGSearch") as MockRAG, \
         patch("src.llm.adapters.agent.WebSearch") as MockWeb:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_rag = MagicMock()
        MockRAG.return_value = mock_rag
        mock_web = MagicMock()
        MockWeb.return_value = mock_web

        from src.llm.adapters.agent import AgentResearcher
        a = AgentResearcher()
        yield a, mock_client, mock_rag, mock_web


class TestShouldForceRag:
    def test_rag_keyword(self):
        from src.llm.adapters.agent import AgentResearcher
        assert AgentResearcher._should_force_rag("use rag to search")
        assert AgentResearcher._should_force_rag("find in my files")
        assert AgentResearcher._should_force_rag("search my document")

    def test_no_rag_keyword(self):
        from src.llm.adapters.agent import AgentResearcher
        assert not AgentResearcher._should_force_rag("what is the weather today")
        assert not AgentResearcher._should_force_rag("hello world")


class TestGetResponse:
    @pytest.mark.asyncio
    async def test_simple_response_no_tools(self, agent):
        a, mock_client, _, _ = agent
        mock_message = MagicMock()
        mock_message.content = "Here is your answer"
        mock_message.tool_calls = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = await a.get_response(SearchRequest(text="hello"))
        assert isinstance(result, SearchResponse)
        assert result.text == "Here is your answer"

    @pytest.mark.asyncio
    async def test_api_error_returns_error(self, agent):
        a, mock_client, _, _ = agent
        mock_client.chat.completions.create.side_effect = Exception("API down")
        result = await a.get_response(SearchRequest(text="test"))
        assert "Error" in result.text

    @pytest.mark.asyncio
    async def test_tool_call_invokes_function(self, agent):
        a, mock_client, mock_rag, _ = agent
        # First response: tool call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "call_rag"
        mock_tool_call.function.arguments = '{"text": "search query"}'
        msg1 = MagicMock()
        msg1.content = None
        msg1.tool_calls = [mock_tool_call]
        resp1 = MagicMock()
        resp1.choices = [MagicMock(message=msg1)]

        # Second response: final
        msg2 = MagicMock()
        msg2.content = "Found results"
        msg2.tool_calls = None
        resp2 = MagicMock()
        resp2.choices = [MagicMock(message=msg2)]

        mock_client.chat.completions.create.side_effect = [resp1, resp2]
        mock_rag.do_search.return_value = MagicMock(text="rag results")

        result = await a.get_response(SearchRequest(text="use rag"))
        assert result.text == "Found results"
        mock_rag.do_search.assert_called_once_with("search query", None)

    @pytest.mark.asyncio
    async def test_unknown_function_returns_error(self, agent):
        a, mock_client, _, _ = agent
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_999"
        mock_tool_call.function.name = "unknown_func"
        mock_tool_call.function.arguments = '{"text": "q"}'
        msg = MagicMock()
        msg.content = None
        msg.tool_calls = [mock_tool_call]
        resp = MagicMock()
        resp.choices = [MagicMock(message=msg)]
        mock_client.chat.completions.create.return_value = resp

        result = await a.get_response(SearchRequest(text="test"))
        assert "Unknown function" in result.text
