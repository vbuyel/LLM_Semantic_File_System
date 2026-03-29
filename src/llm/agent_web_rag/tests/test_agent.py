import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm.agent_web_rag.adapters.agent import AgentResearcher
from src.llm.agent_web_rag.domain.domain import SearchRequest, SearchResponse


class TestAgentResearcher:
    @pytest.fixture
    def mock_env(self):
        with patch.dict(
            "os.environ", {"OPENROUTER_API_KEY": "test_key", "MODEL": "test_model"}
        ):
            yield

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    @patch("src.llm.agent_web_rag.adapters.agent.WebSearch")
    @patch("src.llm.agent_web_rag.adapters.agent.RAGSearch")
    def test_agent_researcher_initialization(
        self, mock_rag, mock_web, mock_openai, mock_env
    ):
        agent = AgentResearcher()
        assert agent.client is not None
        assert agent.model == "test_model"
        assert agent.web is not None
        assert agent.rag is not None

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    def test_get_response_no_tool_calls(self, mock_openai_cls, mock_env):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Final answer", tool_calls=None))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch("src.llm.agent_web_rag.adapters.agent.WebSearch"):
            with patch("src.llm.agent_web_rag.adapters.agent.RAGSearch"):
                agent = AgentResearcher()
                request = SearchRequest(text="test query")
                result = agent.get_response(request)

                assert isinstance(result, SearchResponse)
                assert result.text == "Final answer"

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    def test_get_response_with_web_search_tool(self, mock_openai_cls, mock_env):
        mock_client = Mock()

        tool_call = Mock()
        tool_call.id = "call_123"
        tool_call.function = Mock(
            name="call_web_searcher", arguments='{"text": "search query"}'
        )

        first_response = Mock()
        first_response.choices = [
            Mock(message=Mock(content="", tool_calls=[tool_call]))
        ]

        second_response = Mock()
        second_response.choices = [
            Mock(message=Mock(content="Web search result", tool_calls=None))
        ]

        mock_client.chat.completions.create.side_effect = [
            first_response,
            second_response,
        ]
        mock_openai_cls.return_value = mock_client

        mock_web_search = Mock()
        mock_web_search.do_search.return_value = SearchResponse(
            text="Web search result"
        )

        with patch(
            "src.llm.agent_web_rag.adapters.agent.WebSearch",
            return_value=mock_web_search,
        ):
            with patch("src.llm.agent_web_rag.adapters.agent.RAGSearch"):
                agent = AgentResearcher()
                request = SearchRequest(text="test query")
                result = agent.get_response(request)

                assert isinstance(result, SearchResponse)

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    def test_get_response_with_file_path_includes_rag_instruction(
        self, mock_openai_cls, mock_env
    ):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Final answer", tool_calls=None))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch("src.llm.agent_web_rag.adapters.agent.WebSearch"):
            with patch("src.llm.agent_web_rag.adapters.agent.RAGSearch"):
                agent = AgentResearcher()
                request = SearchRequest(
                    text="analyze file", file_path="/path/to/file.pdf"
                )
                result = agent.get_response(request)

                call_args = mock_client.chat.completions.create.call_args
                system_message = call_args.kwargs["messages"][0]["content"]
                assert "uploaded file" in system_message.lower()
                assert "call_rag" in system_message.lower()

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    def test_get_response_handles_api_exception(self, mock_openai_cls, mock_env):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_cls.return_value = mock_client

        with patch("src.llm.agent_web_rag.adapters.agent.WebSearch"):
            with patch("src.llm.agent_web_rag.adapters.agent.RAGSearch"):
                agent = AgentResearcher()
                request = SearchRequest(text="test query")
                result = agent.get_response(request)

                assert isinstance(result, SearchResponse)
                assert "Error" in result.text

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    def test_get_response_with_unknown_function(self, mock_openai_cls, mock_env):
        mock_client = Mock()

        tool_call = Mock()
        tool_call.id = "call_123"
        tool_call.function = Mock(
            name="unknown_function", arguments='{"text": "query"}'
        )

        response = Mock()
        response.choices = [Mock(message=Mock(content="", tool_calls=[tool_call]))]
        mock_client.chat.completions.create.return_value = response
        mock_openai_cls.return_value = mock_client

        with patch("src.llm.agent_web_rag.adapters.agent.WebSearch"):
            with patch("src.llm.agent_web_rag.adapters.agent.RAGSearch"):
                agent = AgentResearcher()
                request = SearchRequest(text="test query")
                result = agent.get_response(request)

                assert "Unknown function" in result.text

    @patch("src.llm.agent_web_rag.adapters.agent.OpenAI")
    def test_get_response_with_missing_tool_argument(self, mock_openai_cls, mock_env):
        mock_client = Mock()

        tool_call = Mock()
        tool_call.id = "call_123"
        tool_call.function = Mock()
        tool_call.function.name = "call_web_searcher"
        tool_call.function.arguments = "{}"

        response = Mock()
        response.choices = [Mock(message=Mock(content="", tool_calls=[tool_call]))]
        mock_client.chat.completions.create.return_value = response
        mock_openai_cls.return_value = mock_client

        with patch("src.llm.agent_web_rag.adapters.agent.WebSearch"):
            with patch("src.llm.agent_web_rag.adapters.agent.RAGSearch"):
                agent = AgentResearcher()
                request = SearchRequest(text="test query")
                result = agent.get_response(request)

                assert (
                    "missing required argument" in result.text.lower()
                    or "tool call" in result.text.lower()
                )
