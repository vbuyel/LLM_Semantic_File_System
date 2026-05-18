import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from domain.domain import RAGResponse
from adapters.rag_search import RAGSearch


@pytest.fixture
def mock_kafka():
    with patch("adapters.rag_search.Kafka") as mock_class:
        mock_instance = mock_class.return_value
        mock_instance._ensure_connections = AsyncMock()
        mock_instance.send_event = AsyncMock()
        mock_instance.send_command = AsyncMock()
        yield mock_instance


@pytest.mark.asyncio
async def test_rag_search_ensure_started(mock_kafka):
    searcher = RAGSearch()
    assert searcher._started is False

    await searcher._ensure_started()
    assert searcher._started is True
    mock_kafka._ensure_connections.assert_called_once()

    # Second call should not call ensure_connections again
    await searcher._ensure_started()
    mock_kafka._ensure_connections.assert_called_once()


@pytest.mark.asyncio
async def test_rag_search_success_dict_response(mock_kafka):
    # Kafka send_command returns a dictionary with 'data' key containing records
    mock_kafka.send_command.return_value = {
        "data": [
            {
                "file_name": "resume.pdf",
                "file_path": "/home/user/resume.pdf",
                "text_chunk": "This is the resume of John Doe, software developer."
            },
            {
                "file_name": "project.txt",
                "file_path": "/home/user/project.txt",
                "text_chunk": "Project info: Python microservice project."
            }
        ]
    }

    searcher = RAGSearch()
    res = await searcher.do_search("resume info", "john@gmail.com", "corr_123")

    assert isinstance(res, RAGResponse)
    assert "--- Document 1: resume.pdf ---" in res.text
    assert "Path: /home/user/resume.pdf" in res.text
    assert "This is the resume of John Doe" in res.text
    assert "--- Document 2: project.txt ---" in res.text
    assert "Project info:" in res.text

    # Verify event and command parameters
    mock_kafka.send_event.assert_called_once_with("Searching in your files...", "john@gmail.com", "corr_123")
    mock_kafka.send_command.assert_called_once_with("search", "resume info", "john@gmail.com")


@pytest.mark.asyncio
async def test_rag_search_success_list_response(mock_kafka):
    # Kafka send_command returns a list of records directly
    mock_kafka.send_command.return_value = [
        {
            "file_name": "notes.md",
            "file_path": "/home/user/notes.md",
            "text_chunk": "RAG notes"
        }
    ]

    searcher = RAGSearch()
    res = await searcher.do_search("notes", "guest@gmail.com", "corr_123")

    assert "--- Document 1: notes.md ---" in res.text
    assert "RAG notes" in res.text


@pytest.mark.asyncio
async def test_rag_search_success_string_response(mock_kafka):
    # Kafka send_command returns a raw string message directly
    mock_kafka.send_command.return_value = "Custom error or raw data from RAG engine"

    searcher = RAGSearch()
    res = await searcher.do_search("query", "guest@gmail.com", "corr_123")

    assert res.text == "Custom error or raw data from RAG engine"


@pytest.mark.asyncio
async def test_rag_search_empty_records(mock_kafka):
    # Kafka send_command returns empty data
    mock_kafka.send_command.return_value = {"data": []}

    searcher = RAGSearch()
    res = await searcher.do_search("query", "user@gmail.com", "corr_123")

    assert res.text == "No relevant files found in the user's documents."


@pytest.mark.asyncio
async def test_rag_search_non_gmail_owner_fallback(mock_kafka):
    mock_kafka.send_command.return_value = {"data": []}

    searcher = RAGSearch()
    # Non-gmail owner should fall back to 'guest'
    await searcher.do_search("query", "some_user@yahoo.com", "corr_123")

    mock_kafka.send_command.assert_called_once_with("search", "query", "guest")


@pytest.mark.asyncio
async def test_rag_search_null_owner_safeguard(mock_kafka):
    searcher = RAGSearch()
    # If owner is None, it should raise a TypeError which is caught by except block
    res = await searcher.do_search("query", None, "corr_123")

    assert "RAG unavailable:" in res.text
    assert "NoneType" in res.text


@pytest.mark.asyncio
async def test_rag_search_kafka_exception(mock_kafka):
    # Kafka send_command raises Exception
    mock_kafka.send_command.side_effect = Exception("Kafka down")

    searcher = RAGSearch()
    res = await searcher.do_search("query", "user@gmail.com", "corr_123")

    assert res.text == "RAG unavailable: Kafka down"
