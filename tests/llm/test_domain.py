import pytest
from src.llm.domain.domain import RAGRequest, RAGResponse, SearchRequest, SearchResponse


def test_rag_request():
    request = RAGRequest(text="test query")
    assert request.text == "test query"


def test_rag_response():
    response = RAGResponse(text="test response")
    assert response.text == "test response"


def test_search_request():
    request = SearchRequest(text="test query")
    assert request.text == "test query"


def test_search_response():
    response = SearchResponse(text="test response")
    assert response.text == "test response"


def test_rag_request_missing_text():
    with pytest.raises(Exception):
        RAGRequest()


def test_search_request_missing_text():
    with pytest.raises(Exception):
        SearchRequest()
