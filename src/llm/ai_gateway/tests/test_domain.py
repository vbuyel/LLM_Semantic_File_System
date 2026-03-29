import pytest
from src.llm.ai_gateway.domain.domain import Request, Response


class TestRequest:
    def test_request_creation(self):
        request = Request(text="test query", file_path="/path/to/file.pdf")
        assert request.text == "test query"
        assert request.file_path == "/path/to/file.pdf"

    def test_request_optional_file_path(self):
        request = Request(text="test query")
        assert request.text == "test query"
        assert request.file_path is None

    def test_request_with_none_file_path(self):
        request = Request(text="test query", file_path=None)
        assert request.text == "test query"
        assert request.file_path is None


class TestResponse:
    def test_response_creation(self):
        response = Response(text="response text")
        assert response.text == "response text"

    def test_response_with_empty_text(self):
        response = Response(text="")
        assert response.text == ""
