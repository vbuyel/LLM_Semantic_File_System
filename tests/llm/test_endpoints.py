"""Tests for LLM endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.llm.domain.domain import SearchResponse


class TestAIAgentEndpoint:
    def test_get_response_success(self):
        with patch("src.llm.endpoints.main.AgentResearcher") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.get_response.return_value = SearchResponse(text="AI response")
            mock_agent_class.return_value = mock_agent

            from src.llm.endpoints.main import app
            client = TestClient(app)
            response = client.get("/ai_agent", params={"text": "test query"})
            assert response.status_code == 200
            assert response.json()["text"] == "AI response"

    def test_get_response_error(self):
        with patch("src.llm.endpoints.main.AgentResearcher") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.get_response.return_value = SearchResponse(text="Error: something")
            mock_agent_class.return_value = mock_agent

            from src.llm.endpoints.main import app
            client = TestClient(app)
            response = client.get("/ai_agent", params={"text": "test query"})
            assert response.status_code == 200
            data = response.json()
            assert "Error" in data["text"]
