"""Tests for AgentResearcher."""
import pytest
from unittest.mock import patch, MagicMock
from src.llm.domain.domain import SearchRequest, SearchResponse


class TestAgentResearcherInit:
    def test_init(self):
        with patch("src.llm.adapters.agent.OpenAI") as mock_openai,              patch("src.llm.adapters.agent.WebSearch"),              patch("src.llm.adapters.agent.RAGSearch"):
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            from src.llm.adapters.agent import AgentResearcher
            agent = AgentResearcher()
            assert agent.client == mock_client
            assert "call_web_searcher" in agent.tool_functions
            assert "call_rag" in agent.tool_functions


class TestShouldForceRag:
    @pytest.mark.parametrize("text,expected", [
        ("use rag to find my file", True),
        ("rag search", True),
        ("my file about project", True),
        ("find file in my documents", True),
        ("search the web please", False),
        ("what is the weather", False),
    ])
    def test_should_force_rag(self, text, expected):
        from src.llm.adapters.agent import AgentResearcher
        assert AgentResearcher._should_force_rag(text) == expected


class TestGetResponse:
    def test_get_response_with_rag(self):
        with patch("src.llm.adapters.agent.OpenAI") as mock_openai, \
             patch("src.llm.adapters.agent.WebSearch"), \
             patch("src.llm.adapters.agent.RAGSearch"):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "AI response"
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            from src.llm.adapters.agent import AgentResearcher
            agent = AgentResearcher()
            result = agent.get_response(SearchRequest(text="test"))
            assert isinstance(result, SearchResponse)
            assert result.text == "AI response"

    def test_get_response_error(self):
        with patch("src.llm.adapters.agent.OpenAI") as mock_openai,              patch("src.llm.adapters.agent.WebSearch"),              patch("src.llm.adapters.agent.RAGSearch"):
            mock_openai.return_value.chat.completions.create.side_effect = Exception("API error")

            from src.llm.adapters.agent import AgentResearcher
            agent = AgentResearcher()
            result = agent.get_response(SearchRequest(text="test"))
            assert isinstance(result, SearchResponse)
            assert "Error" in result.text
