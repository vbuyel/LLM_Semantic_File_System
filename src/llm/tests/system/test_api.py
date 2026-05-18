import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Note: Because the FastAPI app initializes AgentResearcher at import time, 
# we mock the OpenAI, WebSearch, and RAGSearch classes before importing v1.main.
with patch("adapters.agent.OpenAI"), \
     patch("adapters.agent.WebSearch"), \
     patch("adapters.agent.RAGSearch"):
    from domain.domain import SearchResponse
    from v1.main import app, agent_researcher


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_middleware_headers(client):
    # Test that CORS headers are correctly returned for options requests
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Requested-With",
        },
    )
    assert response.status_code == 200
    # With allow_credentials=True, Starlette CORS middleware returns the specific requesting origin
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-methods") == "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"


def test_get_response_endpoint_success(client):
    # Mock the get_response method with a valid SearchResponse model instance
    mock_response = SearchResponse(text="Answer from mocked AI agent")
    mock_get_response = AsyncMock(return_value=mock_response)
    
    with patch.object(agent_researcher, "get_response", mock_get_response):
        payload = {
            "text": "Who is the owner of this project?",
            "owner": "vlad@gmail.com",
            "correlation_id": "test-correlation-id-abc"
        }
        response = client.post("/get_response", json=payload)
        
        assert response.status_code == 200
        assert response.json() == {"text": "Answer from mocked AI agent"}
        
        # Verify the agent researcher was called with correct data model
        mock_get_response.assert_called_once()
        called_arg = mock_get_response.call_args[0][0]
        assert called_arg.text == "Who is the owner of this project?"
        assert called_arg.owner == "vlad@gmail.com"
        assert called_arg.correlation_id == "test-correlation-id-abc"


def test_get_response_endpoint_invalid_payload(client):
    # Missing required field correlation_id
    payload = {
        "text": "Who is the owner of this project?",
        "owner": "vlad@gmail.com"
    }
    response = client.post("/get_response", json=payload)
    
    # FastAPI automatically validates and returns 422 Unprocessable Entity
    assert response.status_code == 422
    assert "detail" in response.json()
