import urllib.parse
from src.gateway_auth.domain.domain import Settings

settings = Settings()


def generate_google_oauth_redirect_url():
    query_params = {
        "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/auth/google",
        "response_type": "code",
        "scope": " ".join([
            "openid",
            "profile",
            "email",
            "https://www.googleapis.com/auth/drive",
        ]),
        # state ...
    }

    query_string = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{query_string}"
