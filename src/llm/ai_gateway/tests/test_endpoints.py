import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


class TestAIGatewayEndpoints:
    @pytest.fixture
    def mock_agent(self):
        mock_instance = Mock()
        mock_instance.get_response.return_value = Mock(text="Gateway response")
        return mock_instance

    @patch("src.llm.ai_gateway.endpoints.main.AgenticAI")
    def test_post_response_endpoint(self, mock_agent_cls, mock_agent):
        mock_agent_cls.return_value = mock_agent
        from src.llm.ai_gateway.endpoints import main as endpoints_main

        client = TestClient(endpoints_main.app)
        response = client.post("/get_response", json={"text": "test query"})

        assert response.status_code == 200
        assert "text" in response.json()

    @patch("src.llm.ai_gateway.adapters.agentic_ai.requests")
    @patch("src.llm.ai_gateway.endpoints.main.AgenticAI")
    def test_post_response_endpoint_with_file_path(self, mock_agent_cls, mock_requests):
        mock_agent_instance = Mock()
        mock_agent_instance.get_response.return_value = Mock(text="Gateway response")
        mock_agent_cls.return_value = mock_agent_instance

        mock_response = Mock()
        mock_response.text = "Research result"
        mock_requests.get.return_value = mock_response

        from src.llm.ai_gateway.endpoints import main as endpoints_main

        client = TestClient(endpoints_main.app)
        response = client.post(
            "/get_response",
            json={"text": "analyze", "file_path": "/path/to/file.pdf"},
        )

        assert response.status_code == 200

    @patch("src.llm.ai_gateway.endpoints.main.AgenticAI")
    def test_post_response_endpoint_missing_text(self, mock_agent_cls):
        mock_agent_instance = Mock()
        mock_agent_cls.return_value = mock_agent_instance

        from src.llm.ai_gateway.endpoints import main as endpoints_main

        client = TestClient(endpoints_main.app)
        response = client.post("/get_response", json={})

        assert response.status_code == 422
