import urllib.parse
from adapters.oauth_google import generate_google_oauth_redirect_uri
from domain.settings import settings, oauth_states


def test_generate_google_oauth_redirect_uri():
    """Verify Google OAuth redirect URI is correctly generated and the state is stored."""
    # Ensure starting from a clean states set
    oauth_states.clear()

    url = generate_google_oauth_redirect_uri()
    
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    
    # Parse URL to inspect query parameters
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    
    # Check parameters
    assert params["client_id"][0] == settings.OAUTH_GOOGLE_CLIENT_ID
    assert params["redirect_uri"][0] == settings.OAUTH_GOOGLE_REDIRECT_URI
    assert params["response_type"][0] == "code"
    assert params["scope"][0] == " ".join(settings.GOOGLE_DRIVE_SCOPE)
    assert params["access_type"][0] == "offline"
    
    # State validation
    state = params["state"][0]
    assert len(state) > 0
    assert state in oauth_states
