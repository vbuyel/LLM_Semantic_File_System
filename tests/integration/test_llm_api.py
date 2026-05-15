"""
Integration tests for the LLM service FastAPI endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    with patch("src.llm.adapters.agent.OpenAI") as MockOAI, \
         patch("src.llm.adapters.agent.RAGSearch") as MockRAG, \
         patch("src.llm.adapters.agent.WebSearch") as MockWeb:
        MockOAI.return_value = MagicMock()
        MockRAG.return_value = MagicMock()
        MockWeb.return_value = MagicMock()

        from src.llm.v1.main import app
        with TestClient(app) as c:
            yield c


class TestLLMHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestGetResponse:
    def test_get_response_success(self, client):
        with patch("src.llm.endpoints.main.agent_researcher") as mock_agent:
            from src.llm.domain.domain import SearchResponse
            mock_agent.get_response = AsyncMock(return_value=SearchResponse(text="AI answer"))
            resp = client.post("/get_response", json={"text": "test query"})
            assert resp.status_code == 200
            assert resp.json()["text"] == "AI answer"

    def test_get_response_missing_text(self, client):
        resp = client.post("/get_response", json={})
        assert resp.status_code == 422  # validation error
