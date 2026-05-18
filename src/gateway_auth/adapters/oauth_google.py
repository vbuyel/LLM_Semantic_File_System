import urllib.parse
import secrets

from domain.settings import Settings, oauth_states

settings = Settings()


def generate_google_oauth_redirect_uri():
    random_state = secrets.token_urlsafe(16)
    oauth_states.add(random_state)

    query_params = {
        "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
        "redirect_uri": settings.OAUTH_GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.GOOGLE_DRIVE_SCOPE),
        "access_type": "offline",
        "state": random_state,
    }

    query_string = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{query_string}"
