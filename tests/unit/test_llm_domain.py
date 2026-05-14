"""
Unit tests for src.llm.domain.domain models.
"""
import pytest
from src.llm.domain.domain import RAGRequest, RAGResponse, SearchRequest, SearchResponse

pytestmark = pytest.mark.unit


class TestRAGRequest:
    def test_create(self):
        r = RAGRequest(text="search query")
        assert r.text == "search query"

    def test_missing_text(self):
        with pytest.raises(Exception):
            RAGRequest()


class TestRAGResponse:
    def test_create(self):
        r = RAGResponse(text="result data")
        assert r.text == "result data"

    def test_serialization(self):
        r = RAGResponse(text="test")
        assert r.model_dump() == {"text": "test"}


class TestSearchRequest:
    def test_create(self):
        r = SearchRequest(text="find documents about AI", owner="test-owner")
        assert "AI" in r.text
        assert r.owner == "test-owner"


class TestSearchResponse:
    def test_create(self):
        r = SearchResponse(text="Here are the results...")
        assert r.text.startswith("Here")

    def test_json_roundtrip(self):
        r = SearchResponse(text="data")
        restored = SearchResponse.model_validate_json(r.model_dump_json())
        assert restored == r
