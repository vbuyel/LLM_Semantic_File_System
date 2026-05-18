import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from domain.domain import SearchResponse
from adapters.web_search import WebSearch


@pytest.fixture
def mock_dependencies():
    with patch("adapters.web_search.AsyncExa") as mock_exa_class, \
         patch("adapters.web_search.Kafka") as mock_kafka_class:
        
        mock_exa_instance = mock_exa_class.return_value
        mock_exa_instance.search = AsyncMock()
        
        mock_kafka_instance = mock_kafka_class.return_value
        mock_kafka_instance._ensure_connections = AsyncMock()
        mock_kafka_instance.send_event = AsyncMock()
        
        yield {
            "exa": mock_exa_instance,
            "kafka": mock_kafka_instance
        }


@pytest.mark.asyncio
async def test_web_search_ensure_started(mock_dependencies):
    searcher = WebSearch()
    assert searcher._started is False

    await searcher._ensure_started()
    assert searcher._started is True
    mock_dependencies["kafka"]._ensure_connections.assert_called_once()


@pytest.mark.asyncio
async def test_web_search_success(mock_dependencies):
    mock_exa = mock_dependencies["exa"]
    mock_kafka = mock_dependencies["kafka"]

    # Setup mocked search results
    mock_result_1 = MagicMock()
    mock_result_1.title = "Python Tutorial"
    mock_result_1.url = "https://python.org"
    mock_result_1.highlights = ["Python is a programming language", "Great for AI"]
    mock_result_1.text = "Full text here..."

    mock_result_2 = MagicMock()
    mock_result_2.title = None # Test untitled fallback
    mock_result_2.url = None   # Test missing url
    mock_result_2.highlights = []
    mock_result_2.text = "This is a body text without highlights. It should show the first 500 chars."

    mock_search_response = MagicMock()
    mock_search_response.results = [mock_result_1, mock_result_2]
    mock_exa.search.return_value = mock_search_response

    searcher = WebSearch()
    res = await searcher.do_search("python", "user@gmail.com", "corr_999")

    assert isinstance(res, SearchResponse)
    
    # Check that event was sent
    mock_kafka.send_event.assert_called_once_with("Searching in web...", "user@gmail.com", "corr_999")
    
    # Check exa search call parameters
    mock_exa.search.assert_called_once_with("python", num_results=10, contents={"highlights": True})

    # Check formatting of the results
    lines = res.text.split("\n")
    assert "1. Python Tutorial" in lines
    assert "   URL: https://python.org" in lines
    assert "   Python is a programming language" in lines
    assert "   Great for AI" in lines
    
    # Check fallback for result 2
    assert "2. Untitled" in lines
    assert "   This is a body text without highlights." in res.text


@pytest.mark.asyncio
async def test_web_search_no_results(mock_dependencies):
    mock_exa = mock_dependencies["exa"]
    mock_search_response = MagicMock()
    mock_search_response.results = []
    mock_exa.search.return_value = mock_search_response

    searcher = WebSearch()
    res = await searcher.do_search("query", "user", "corr_id")

    assert res.text == "No search results found."


@pytest.mark.asyncio
async def test_web_search_failure(mock_dependencies):
    mock_exa = mock_dependencies["exa"]
    # Mocking Exa API throwing error
    mock_exa.search.side_effect = Exception("Exa API Rate Limit Exceeded")

    searcher = WebSearch()
    res = await searcher.do_search("query", "user", "corr_id")

    # Should catch error and return fallback message
    assert res.text == "Web search unavailable. Please try again later."
