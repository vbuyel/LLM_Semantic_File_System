import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from src.llm.ai_gateway.adapters.agentic_ai import AgenticAI
from src.llm.ai_gateway.domain.domain import Request, Response


class TestAgenticAI:
    @pytest.fixture
    def mock_env(self):
        with patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test_key",
                "MODEL": "test_model",
                "LSFS_URL": "http://localhost",
            },
        ):
            yield

    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_agentic_ai_initialization(self, mock_openai, mock_env):
        agent = AgenticAI()
        assert agent.client is not None
        assert agent.model == "test_model"

    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_get_response_no_tool_calls(self, mock_openai_cls, mock_env):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Direct answer", tool_calls=None))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        agent = AgenticAI()
        request = Request(text="test query")
        result = agent.get_response(request)

        assert isinstance(result, Response)
        assert result.text == "Direct answer"

    @patch("src.llm.ai_gateway.adapters.agentic_ai.requests")
    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_get_response_with_tool_call(
        self, mock_openai_cls, mock_requests, mock_env
    ):
        mock_client = Mock()

        tool_call = Mock()
        tool_call.id = "call_123"
        tool_call.function = Mock(
            name="call_agent_researcher",
            arguments='{"text": "search query", "file_path": "/path/to/file.pdf"}',
        )

        first_response = Mock()
        first_response.choices = [
            Mock(message=Mock(content="", tool_calls=[tool_call]))
        ]

        second_response = Mock()
        second_response.choices = [
            Mock(message=Mock(content="Research result", tool_calls=None))
        ]

        mock_client.chat.completions.create.side_effect = [
            first_response,
            second_response,
        ]
        mock_openai_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Research result"
        mock_requests.get.return_value = mock_response

        agent = AgenticAI()
        request = Request(text="test query")
        result = agent.get_response(request)

        assert isinstance(result, Response)

    @patch("src.llm.ai_gateway.adapters.agentic_ai.requests")
    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_get_response_with_file_path_includes_context(
        self, mock_openai_cls, mock_requests, mock_env
    ):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Answer", tool_calls=None))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        agent = AgenticAI()
        request = Request(text="analyze", file_path="/path/to/file.pdf")
        result = agent.get_response(request)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_messages = [
            msg["content"] for msg in messages if msg.get("role") == "system"
        ]
        assert any(
            "file_path" in msg or "uploaded" in msg.lower() for msg in system_messages
        )

    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_get_response_handles_api_exception(self, mock_openai_cls, mock_env):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_cls.return_value = mock_client

        agent = AgenticAI()
        request = Request(text="test query")
        result = agent.get_response(request)

        assert isinstance(result, Response)
        assert "Error" in result.text

    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_get_response_with_unknown_function(self, mock_openai_cls, mock_env):
        mock_client = Mock()

        tool_call = Mock()
        tool_call.id = "call_123"
        tool_call.function = Mock(name="unknown_tool", arguments='{"text": "query"}')

        response = Mock()
        response.choices = [Mock(message=Mock(content="", tool_calls=[tool_call]))]
        mock_client.chat.completions.create.return_value = response
        mock_openai_cls.return_value = mock_client

        agent = AgenticAI()
        request = Request(text="test query")
        result = agent.get_response(request)

        assert "Unknown function" in result.text

    @patch("src.llm.ai_gateway.adapters.agentic_ai.requests")
    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_call_agent_researcher_with_file_path(
        self, mock_openai_cls, mock_requests, mock_env
    ):
        mock_client = Mock()
        mock_openai_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Research result"
        mock_requests.get.return_value = mock_response

        agent = AgenticAI()
        request = Request(text="search query", file_path="/path/to/file.pdf")
        result = agent._call_agent_researcher(request)

        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        assert "file_path" in call_args.kwargs["params"] or "file_path" in str(
            call_args
        )

    @patch("src.llm.ai_gateway.adapters.agentic_ai.requests")
    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_call_agent_researcher_without_file_path(
        self, mock_openai_cls, mock_requests, mock_env
    ):
        mock_client = Mock()
        mock_openai_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "Research result"
        mock_requests.get.return_value = mock_response

        agent = AgenticAI()
        request = Request(text="search query")
        result = agent._call_agent_researcher(request)

        mock_requests.get.assert_called_once()

    @patch("src.llm.ai_gateway.adapters.agentic_ai.OpenAI")
    def test_get_response_tool_exception(self, mock_openai_cls, mock_env):
        mock_client = Mock()

        tool_call = Mock()
        tool_call.id = "call_123"
        tool_call.function = Mock()
        tool_call.function.name = "call_agent_researcher"
        tool_call.function.arguments = '{"text": "search query"}'

        first_response = Mock()
        first_response.choices = [
            Mock(message=Mock(content="", tool_calls=[tool_call]))
        ]

        mock_client.chat.completions.create.return_value = first_response
        mock_openai_cls.return_value = mock_client

        with patch("src.llm.ai_gateway.adapters.agentic_ai.requests") as mock_requests:
            mock_requests.get.side_effect = ConnectionError("Connection refused")

            agent = AgenticAI()
            request = Request(text="test query")

            try:
                result = agent.get_response(request)
            except ConnectionError:
                pass

            assert mock_requests.get.called
