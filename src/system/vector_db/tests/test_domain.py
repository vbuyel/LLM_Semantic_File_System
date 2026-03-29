import pytest
from datetime import datetime
from src.system.vector_db.domain.domain import (
    DocumentCreate,
    DocumentResponse,
    DocumentSearch,
    SearchResult,
)


class TestDocumentCreate:
    def test_document_create_with_embedding(self):
        doc = DocumentCreate(embedding=[0.1, 0.2, 0.3])
        assert doc.embedding == [0.1, 0.2, 0.3]
        assert doc.metadata is None

    def test_document_create_with_metadata(self):
        doc = DocumentCreate(embedding=[0.1, 0.2, 0.3], metadata={"key": "value"})
        assert doc.embedding == [0.1, 0.2, 0.3]
        assert doc.metadata == {"key": "value"}

    def test_document_create_with_empty_embedding(self):
        doc = DocumentCreate(embedding=[])
        assert doc.embedding == []


class TestDocumentResponse:
    def test_document_response_creation(self):
        now = datetime.now()
        doc = DocumentResponse(id=1, metadata={"key": "value"}, created_at=now)
        assert doc.id == 1
        assert doc.metadata == {"key": "value"}
        assert doc.created_at == now

    def test_document_response_optional_metadata(self):
        now = datetime.now()
        doc = DocumentResponse(id=1, metadata=None, created_at=now)
        assert doc.id == 1
        assert doc.metadata is None


class TestDocumentSearch:
    def test_document_search_creation(self):
        search = DocumentSearch(embedding=[0.1, 0.2, 0.3])
        assert search.embedding == [0.1, 0.2, 0.3]
        assert search.limit == 3

    def test_document_search_with_custom_limit(self):
        search = DocumentSearch(embedding=[0.1, 0.2, 0.3], limit=10)
        assert search.embedding == [0.1, 0.2, 0.3]
        assert search.limit == 10


class TestSearchResult:
    def test_search_result_creation(self):
        now = datetime.now()
        result = SearchResult(
            id=1, metadata={"key": "value"}, created_at=now, distance=0.5
        )
        assert result.id == 1
        assert result.metadata == {"key": "value"}
        assert result.created_at == now
        assert result.distance == 0.5

    def test_search_result_optional_metadata(self):
        now = datetime.now()
        result = SearchResult(id=1, metadata=None, created_at=now, distance=0.5)
        assert result.id == 1
        assert result.metadata is None

    def test_search_result_zero_distance(self):
        now = datetime.now()
        result = SearchResult(id=1, metadata=None, created_at=now, distance=0.0)
        assert result.distance == 0.0
