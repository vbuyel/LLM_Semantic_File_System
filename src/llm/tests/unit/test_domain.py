import pytest
from pydantic import ValidationError
from domain.domain import RAGRequest, RAGResponse, SearchRequest, SearchResponse


def test_rag_request_validation():
    # Valid request
    req = RAGRequest(text="hello")
    assert req.text == "hello"

    # Missing text should raise ValidationError
    with pytest.raises(ValidationError):
        RAGRequest()


def test_rag_response_validation():
    # Valid response
    res = RAGResponse(text="response text")
    assert res.text == "response text"

    # Missing text should raise ValidationError
    with pytest.raises(ValidationError):
        RAGResponse()


def test_search_request_validation():
    # Valid request
    req = SearchRequest(text="search query", owner="user@gmail.com", correlation_id="12345")
    assert req.text == "search query"
    assert req.owner == "user@gmail.com"
    assert req.correlation_id == "12345"

    # Missing fields should raise ValidationError
    with pytest.raises(ValidationError):
        SearchRequest(text="only text")


def test_search_response_validation():
    # Valid response
    res = SearchResponse(text="search results")
    assert res.text == "search results"

    # Missing text should raise ValidationError
    with pytest.raises(ValidationError):
        SearchResponse()
