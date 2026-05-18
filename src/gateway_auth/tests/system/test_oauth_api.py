from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi import status

from v1.main import app
from domain.settings import oauth_states


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_oauth_states():
    oauth_states.clear()
    yield
    oauth_states.clear()


def test_get_google_oauth_url(client):
    """Verify that GET /auth/google/url redirects (302) to google accounts URL and registers state."""
    response = client.get("/auth/google/url", follow_redirects=False)
    
    assert response.status_code == status.HTTP_302_FOUND
    location = response.headers["Location"]
    assert "https://accounts.google.com/o/oauth2/v2/auth" in location
    assert "state=" in location

    # The generated state should be recorded
    assert len(oauth_states) == 1
    state = list(oauth_states)[0]
    assert f"state={state}" in location


def test_oauth_callback_invalid_state(client):
    """Verify that POST /auth/google/callback fails with 400 Bad Request when state is invalid."""
    response = client.post(
        "/auth/google/callback",
        json={"code": "auth-code-123", "state": "invalid-state-xyz"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid state" in response.json()["detail"]


@patch("v1.oauth_router.jwt.decode")
@patch("v1.oauth_router.aiohttp.ClientSession")
def test_oauth_callback_success(mock_session_class, mock_jwt_decode, client):
    """Verify successful OAuth callback exchange and JWT decoding."""
    # Pre-populate state
    state = "valid-state-123"
    oauth_states.add(state)

    # Set up mock Google token response
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "access_token": "google-access-token",
        "id_token": "google-id-token",
    })
    
    mock_session_instance = MagicMock()
    # Mock __aenter__ and __aexit__ for session.post context manager
    mock_post_context = MagicMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    
    mock_session_instance.post.return_value = mock_post_context
    mock_session_class.return_value.__aenter__.return_value = mock_session_instance

    # Mock JWT decoding
    mock_decoded_user = {
        "email": "test@example.com",
        "name": "Test User",
        "sub": "google-user-id",
    }
    mock_jwt_decode.return_value = mock_decoded_user

    response = client.post(
        "/auth/google/callback",
        json={"code": "valid-code", "state": state}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["access_token"] == "google-access-token"
    assert data["user"] == mock_decoded_user
    
    # State should be discarded after use
    assert state not in oauth_states
    mock_jwt_decode.assert_called_once_with(
        "google-id-token",
        algorithms=["RS256"],
        options={"verify_signature": False}
    )


@patch("v1.oauth_router.aiohttp.ClientSession")
def test_oauth_callback_google_error(mock_session_class, client):
    """Verify callback handles Google token endpoint returning an error."""
    state = "valid-state-123"
    oauth_states.add(state)

    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"error": "invalid_grant"})
    
    mock_session_instance = MagicMock()
    mock_post_context = MagicMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    
    mock_session_instance.post.return_value = mock_post_context
    mock_session_class.return_value.__aenter__.return_value = mock_session_instance

    response = client.post(
        "/auth/google/callback",
        json={"code": "bad-code", "state": state}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid_grant" in response.json()["detail"]
    assert state not in oauth_states  # discarded anyway


@patch("v1.oauth_router.aiohttp.ClientSession")
def test_oauth_callback_parse_error(mock_session_class, client):
    """Verify callback handles network/parse exceptions from token response."""
    state = "valid-state-123"
    oauth_states.add(state)

    mock_response = AsyncMock()
    mock_response.json.side_effect = Exception("JSON parsing failed")
    
    mock_session_instance = MagicMock()
    mock_post_context = MagicMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    
    mock_session_instance.post.return_value = mock_post_context
    mock_session_class.return_value.__aenter__.return_value = mock_session_instance

    response = client.post(
        "/auth/google/callback",
        json={"code": "valid-code", "state": state}
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to parse Google response" in response.json()["detail"]
