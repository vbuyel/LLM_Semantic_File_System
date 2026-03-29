import pytest
from src.llm.agent_web_rag.domain.domain import (
    RAGRequest,
    RAGResponse,
    DataForExtraction,
    DataExtracted,
    SearchRequest,
    SearchResponse,
)


class TestRAGRequest:
    def test_rag_request_creation(self):
        request = RAGRequest(text="test query", additional_data="some file content")
        assert request.text == "test query"
        assert request.additional_data == "some file content"

    def test_rag_request_optional_additional_data(self):
        request = RAGRequest(text="test query")
        assert request.text == "test query"
        assert request.additional_data is None

    def test_rag_request_with_list_additional_data_fails(self):
        with pytest.raises(Exception):
            RAGRequest(text="test query", additional_data=["chunk1", "chunk2"])


class TestRAGResponse:
    def test_rag_response_creation(self):
        response = RAGResponse(text="extracted content")
        assert response.text == "extracted content"


class TestDataForExtraction:
    def test_data_for_extraction_creation(self):
        data = DataForExtraction(text="query", additional_data=["chunk1", "chunk2"])
        assert data.text == "query"
        assert data.additional_data == ["chunk1", "chunk2"]

    def test_data_for_extraction_requires_text(self):
        with pytest.raises(ValueError):
            DataForExtraction(additional_data=["chunk1"])

    def test_data_for_extraction_requires_additional_data(self):
        with pytest.raises(ValueError):
            DataForExtraction(text="query")


class TestDataExtracted:
    def test_data_extracted_creation(self):
        data = DataExtracted(text="extracted text")
        assert data.text == "extracted text"


class TestSearchRequest:
    def test_search_request_creation(self):
        request = SearchRequest(text="search query", file_path="/path/to/file.pdf")
        assert request.text == "search query"
        assert request.file_path == "/path/to/file.pdf"

    def test_search_request_optional_file_path(self):
        request = SearchRequest(text="search query")
        assert request.text == "search query"
        assert request.file_path is None


class TestSearchResponse:
    def test_search_response_creation(self):
        response = SearchResponse(text="response text")
        assert response.text == "response text"
