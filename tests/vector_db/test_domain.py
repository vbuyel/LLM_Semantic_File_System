import pytest
from datetime import datetime
from pydantic import ValidationError
from src.vector_db.domain.domain import DocMetadata, RAGResults


class TestDocMetadata:
    def test_doc_metadata_creation_valid(self):
        doc = DocMetadata(
            id=1,
            created_at=datetime.now(),
            file_name="test.txt",
            file_path="/path/to/test.txt",
            text_chunk="This is a test chunk",
        )
        assert doc.id == 1
        assert isinstance(doc.created_at, datetime)
        assert doc.file_name == "test.txt"
        assert doc.file_path == "/path/to/test.txt"
        assert doc.text_chunk == "This is a test chunk"

    def test_doc_metadata_creation_with_none_values(self):
        with pytest.raises(ValidationError):
            DocMetadata(
                id=None,
                created_at=datetime.now(),
                file_name="test.txt",
                file_path="/path/to/test.txt",
                text_chunk="This is a test chunk",
            )

    def test_doc_metadata_missing_fields(self):
        with pytest.raises(ValidationError):
            DocMetadata()

    def test_doc_metadata_serialization(self):
        now = datetime.now()
        doc = DocMetadata(
            id=1,
            created_at=now,
            file_name="test.txt",
            file_path="/path/to/test.txt",
            text_chunk="This is a test chunk",
        )
        doc_dict = doc.model_dump()
        assert doc_dict["id"] == 1
        assert doc_dict["created_at"] == now
        assert doc_dict["file_name"] == "test.txt"
        assert doc_dict["file_path"] == "/path/to/test.txt"
        assert doc_dict["text_chunk"] == "This is a test chunk"

    def test_doc_metadata_from_dict(self):
        now = datetime.now()
        data = {
            "id": 1,
            "created_at": now,
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "text_chunk": "This is a test chunk",
        }
        doc = DocMetadata.model_validate(data)
        assert doc.id == 1
        assert doc.created_at == now
        assert doc.file_name == "test.txt"
        assert doc.file_path == "/path/to/test.txt"
        assert doc.text_chunk == "This is a test chunk"


class TestRAGResults:
    def test_rag_results_creation_with_data(self):
        doc = DocMetadata(
            id=1,
            created_at=datetime.now(),
            file_name="test.txt",
            file_path="/path/to/test.txt",
            text_chunk="This is a test chunk",
        )
        results = RAGResults(data=[doc])
        assert results.data is not None
        assert len(results.data) == 1
        assert results.data[0].id == 1
        assert results.data[0].file_name == "test.txt"

    def test_rag_results_creation_with_none(self):
        results = RAGResults(data=None)
        assert results.data is None

    def test_rag_results_default_creation(self):
        results = RAGResults()
        assert results.data is None

    def test_rag_results_empty_list(self):
        results = RAGResults(data=[])
        assert results.data == []

    def test_rag_results_serialization(self):
        doc = DocMetadata(
            id=1,
            created_at=datetime.now(),
            file_name="test.txt",
            file_path="/path/to/test.txt",
            text_chunk="This is a test chunk",
        )
        results = RAGResults(data=[doc])
        results_dict = results.model_dump()
        assert results_dict["data"] is not None
        assert len(results_dict["data"]) == 1
        assert results_dict["data"][0]["id"] == 1
        assert results_dict["data"][0]["file_name"] == "test.txt"

    def test_rag_results_from_dict(self):
        doc_data = {
            "id": 1,
            "created_at": datetime.now().isoformat(),
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "text_chunk": "This is a test chunk",
        }
        results_data = {"data": [doc_data]}
        results = RAGResults.model_validate(results_data)
        assert results.data is not None
        assert len(results.data) == 1
        assert results.data[0].id == 1
        assert results.data[0].file_name == "test.txt"
