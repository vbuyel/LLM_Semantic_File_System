import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


# We patch database connection and sentence-transformers in v1.main to avoid
# attempting real connections at import time.
with patch("adapters.database.psycopg.connect"), \
     patch("adapters.database.register_vector"), \
     patch("adapters.database.SentenceTransformer"):
    from v1.main import app, get_db


@pytest.fixture
def client():
    # Use TestClient for system endpoint tests
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert json_data["service"] == "vector_db"
    assert "consumer_alive" in json_data


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
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-methods") == "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"


def test_check_file_exists_endpoint_true(client):
    mock_db = MagicMock()
    mock_db._file_exists.return_value = True
    
    with patch("v1.main.get_db", return_value=mock_db):
        params = {
            "file_path": "docs/",
            "file_name": "resume.pdf",
            "file_size": 1024
        }
        response = client.get("/check-file-exists", params=params)
        
        assert response.status_code == 200
        assert response.json() == {"exists": True}
        
        # Verify it called the database with correct params
        mock_db._file_exists.assert_called_once_with("docs/", "resume.pdf", 1024)


def test_check_file_exists_endpoint_false(client):
    mock_db = MagicMock()
    mock_db._file_exists.return_value = False
    
    with patch("v1.main.get_db", return_value=mock_db):
        params = {
            "file_path": "docs/",
            "file_name": "unknown.pdf",
            "file_size": 9999
        }
        response = client.get("/check-file-exists", params=params)
        
        assert response.status_code == 200
        assert response.json() == {"exists": False}
        
        mock_db._file_exists.assert_called_once_with("docs/", "unknown.pdf", 9999)


def test_check_file_exists_endpoint_invalid_params(client):
    # Missing required query parameters (like file_name and file_size)
    params = {
        "file_path": "docs/"
    }
    response = client.get("/check-file-exists", params=params)
    
    # Should raise validation error (422 Unprocessable Entity)
    assert response.status_code == 422
    assert "detail" in response.json()
