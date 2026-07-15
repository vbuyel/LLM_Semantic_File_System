import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from domain.domain import SearchRequest, SearchResponse
from adapters.agent import AgentResearcher


# Mock classes to prevent actual initialization side effects (like connecting to Kafka or Exa)
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("adapters.agent.OpenAI") as mock_openai, \
         patch("adapters.agent.WebSearch") as mock_web, \
         patch("adapters.agent.RAGSearch") as mock_rag:
        
        # Setup mock openai client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        yield {
            "openai_client": mock_client,
            "web_search": mock_web.return_value,
            "rag_search": mock_rag.return_value
        }


def test_should_force_rag_hints():
    # Russian hints
    assert AgentResearcher._should_force_rag("покажи мне этот файл") is True
    assert AgentResearcher._should_force_rag("где находится документ?") is True

    # English hints
    assert AgentResearcher._should_force_rag("use rag please") is True
    assert AgentResearcher._should_force_rag("read my files") is True
    assert AgentResearcher._should_force_rag("find file about python") is True

    # File extensions
    assert AgentResearcher._should_force_rag("look in main.py") is True
    assert AgentResearcher._should_force_rag("what is inside resume.pdf?") is True
    assert AgentResearcher._should_force_rag("config.yaml settings") is True

    # CamelCase/Underscore/Dash patterns (like database table names, environment configs, identifier styles)
    assert AgentResearcher._should_force_rag("Check the User_Profile table") is True
    assert AgentResearcher._should_force_rag("Look for Data-Source config") is True

    # Non-hints
    assert AgentResearcher._should_force_rag("What is the capital of France?") is False
    assert AgentResearcher._should_force_rag("Explain how quantum computing works.") is False


def test_assistant_message_payload():
    # Plain message
    msg = MagicMock()
    msg.content = "Hello there!"
    msg.tool_calls = None
    
    payload = AgentResearcher._assistant_message_payload(msg)
    assert payload == {"role": "assistant", "content": "Hello there!"}

    # Message with tool calls
    tool_call = MagicMock()
    tool_call.id = "call_123"
    tool_call.function.name = "call_rag"
    tool_call.function.arguments = '{"text": "query"}'
    msg.tool_calls = [tool_call]

    payload = AgentResearcher._assistant_message_payload(msg)
    assert payload == {
        "role": "assistant",
        "content": "Hello there!",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "call_rag",
                    "arguments": '{"text": "query"}'
                }
            }
        ]
    }

    # Gemini 3 thought_signature must round-trip on follow-up tool turns
    tool_call.extra_content = {
        "google": {"thought_signature": "sig-abc123"}
    }
    payload = AgentResearcher._assistant_message_payload(msg)
    assert payload["tool_calls"][0]["extra_content"] == {
        "google": {"thought_signature": "sig-abc123"}
    }


@pytest.mark.asyncio
async def test_get_response_no_tools(mock_dependencies):
    # Setup mock OpenAI response
    mock_client = mock_dependencies["openai_client"]
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Hello! I am your assistant.", tool_calls=None))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    researcher = AgentResearcher()
    request = SearchRequest(text="Hello", owner="user", correlation_id="123")
    
    res = await researcher.get_response(request)
    assert isinstance(res, SearchResponse)
    assert res.text == "Hello! I am your assistant."
    
    # Check OpenAI was called with correct parameters
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert kwargs["messages"][-1]["content"] == "Hello"
    assert "tool_choice" not in kwargs


@pytest.mark.asyncio
async def test_get_response_force_rag(mock_dependencies):
    mock_client = mock_dependencies["openai_client"]
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Found in file", tool_calls=None))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    researcher = AgentResearcher()
    request = SearchRequest(text="Read my file.txt", owner="user", correlation_id="123")
    
    await researcher.get_response(request)
    
    # Verify tool_choice is forced to call_rag
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "call_rag"},
    }


@pytest.mark.asyncio
async def test_get_response_with_tool_call_loop(mock_dependencies):
    mock_client = mock_dependencies["openai_client"]
    mock_web = mock_dependencies["web_search"]
    
    # Mock web search result
    mock_web.do_search = AsyncMock(return_value=MagicMock(text="Web results content"))

    # First OpenAI call returns a tool call to call_web_searcher
    tool_call = MagicMock()
    tool_call.id = "call_web"
    tool_call.function.name = "call_web_searcher"
    tool_call.function.arguments = '{"text": "python news"}'
    
    first_msg = MagicMock(content=None, tool_calls=[tool_call])
    first_response = MagicMock()
    first_response.choices = [MagicMock(message=first_msg)]

    # Second OpenAI call returns final answer
    second_msg = MagicMock(content="Here is the python news from the web...", tool_calls=None)
    second_response = MagicMock()
    second_response.choices = [MagicMock(message=second_msg)]

    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    researcher = AgentResearcher()
    request = SearchRequest(text="Search python news", owner="user@gmail.com", correlation_id="123")
    
    res = await researcher.get_response(request)
    assert res.text == "Here is the python news from the web..."
    
    # Verify web search was invoked
    mock_web.do_search.assert_called_once_with("python news", "user@gmail.com", "123")
    
    # Verify OpenAI was called twice
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_get_response_openai_error(mock_dependencies):
    mock_client = mock_dependencies["openai_client"]
    mock_client.chat.completions.create.side_effect = Exception("API error")

    researcher = AgentResearcher()
    request = SearchRequest(text="Hello", owner="user", correlation_id="123")
    
    res = await researcher.get_response(request)
    assert "Error: API error" in res.text


@pytest.mark.asyncio
async def test_get_response_invalid_tool_json(mock_dependencies):
    mock_client = mock_dependencies["openai_client"]
    
    # OpenAI returns a tool call with invalid JSON in arguments
    tool_call = MagicMock()
    tool_call.id = "call_bad_json"
    tool_call.function.name = "call_web_searcher"
    tool_call.function.arguments = '{invalid json}'
    
    msg = MagicMock(content=None, tool_calls=[tool_call])
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    mock_client.chat.completions.create.return_value = response

    researcher = AgentResearcher()
    request = SearchRequest(text="Search", owner="user", correlation_id="123")
    
    res = await researcher.get_response(request)
    assert "Invalid JSON args for function: call_web_searcher" in res.text


@pytest.mark.asyncio
async def test_get_response_missing_tool_text_arg(mock_dependencies):
    mock_client = mock_dependencies["openai_client"]
    
    # OpenAI returns a tool call missing the required "text" argument
    tool_call = MagicMock()
    tool_call.id = "call_missing_arg"
    tool_call.function.name = "call_web_searcher"
    tool_call.function.arguments = '{"not_text": "something"}'
    
    msg = MagicMock(content=None, tool_calls=[tool_call])
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    mock_client.chat.completions.create.return_value = response

    researcher = AgentResearcher()
    request = SearchRequest(text="Search", owner="user", correlation_id="123")
    
    res = await researcher.get_response(request)
    assert "Tool call missing required argument: text" in res.text


@pytest.mark.asyncio
async def test_get_response_unknown_tool_function(mock_dependencies):
    mock_client = mock_dependencies["openai_client"]
    
    # OpenAI returns an unknown tool call name
    tool_call = MagicMock()
    tool_call.id = "call_unknown"
    tool_call.function.name = "non_existent_tool"
    tool_call.function.arguments = '{"text": "query"}'
    
    msg = MagicMock(content=None, tool_calls=[tool_call])
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    mock_client.chat.completions.create.return_value = response

    researcher = AgentResearcher()
    request = SearchRequest(text="Search", owner="user", correlation_id="123")
    
    res = await researcher.get_response(request)
    assert "Unknown function: non_existent_tool" in res.text
