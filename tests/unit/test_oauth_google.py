"""
Unit tests for src.gateway_auth.adapters.oauth_google.
"""
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings(monkeypatch):
    """Provide mock settings for OAuth."""
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("OAUTH_GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    monkeypatch.setenv("OAUTH_GOOGLE_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("AGENT_SERVER", "http://localhost:8001")
    monkeypatch.setenv("FILE_OPS_SERVER", "http://localhost:8002")


class TestGenerateOAuthRedirectUri:
    def test_returns_google_url(self, mock_settings):
        with patch("src.gateway_auth.adapters.oauth_google.Settings") as MockSettings:
            mock_s = MagicMock()
            mock_s.OAUTH_GOOGLE_CLIENT_ID = "test-client-id"
            mock_s.OAUTH_GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/callback"
            mock_s.GOOGLE_DRIVE_SCOPE = ["openid", "email"]
            MockSettings.return_value = mock_s

            with patch("src.gateway_auth.adapters.oauth_google.settings", mock_s):
                from src.gateway_auth.adapters.oauth_google import generate_google_oauth_redirect_uri
                from src.gateway_auth.domain.settings import oauth_states

                uri = generate_google_oauth_redirect_uri()
                assert "accounts.google.com" in uri
                assert "client_id=test-client-id" in uri
                assert "response_type=code" in uri
                # State should be stored
                assert len(oauth_states) > 0
