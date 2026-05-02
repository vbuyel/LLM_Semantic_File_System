from fastapi import status, APIRouter, Body
from typing import Annotated
from fastapi.responses import RedirectResponse
import aiohttp
import jwt

from src.gateway_auth.adapters.oauth_google import generate_google_oauth_redirect_uri
from src.gateway_auth.domain.settings import settings, oauth_states


oauth_router = APIRouter(prefix="/auth")


@oauth_router.get("/google/url")
def get_google_oauth_redirect_url():
    uri = generate_google_oauth_redirect_uri()
    return RedirectResponse(url=uri, status_code=302)


@oauth_router.post("/google/callback")
async def handle_google_oauth_callback(
    code: Annotated[str, Body()],
    state: Annotated[str, Body()],
):
    # Validate state for CSRF protection
    if state not in oauth_states:
        return {"error": "Invalid state"}, status.HTTP_400_BAD_REQUEST
    oauth_states.discard(state)

    google_token_url = "https://oauth2.googleapis.com/token"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=google_token_url,
            data={
                "code": code,
                "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
                "client_secret": settings.OAUTH_GOOGLE_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": settings.OAUTH_GOOGLE_REDIRECT_URI,
            },
            ssl=False,
        ) as response:
            try:
                result = await response.json()
            except Exception as e:
                return {"error": f"Failed to parse Google response: {e}"}, status.HTTP_500_INTERNAL_SERVER_ERROR

            if "error" in result:
                return {"error": result.get("error", "Unknown error")}, status.HTTP_400_BAD_REQUEST

            id_token = result.get("id_token")
            access_token = result.get("access_token")
            if not id_token:
                return {"error": "No id_token in response"}, status.HTTP_400_BAD_REQUEST

            user_data = jwt.decode(
                            id_token,
                            algorithms=["RS256"],
                            options={"verify_signature": False},
                        )
    return {
        "user": user_data,
        "access_token": access_token,
    }
