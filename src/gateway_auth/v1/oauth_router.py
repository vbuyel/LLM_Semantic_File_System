from fastapi import status, APIRouter, Body, HTTPException
from typing import Annotated
from fastapi.responses import RedirectResponse
from fastapi import status
import aiohttp
import jwt

from adapters.oauth_google import generate_google_oauth_redirect_uri
from domain.settings import settings, oauth_states


oauth_router = APIRouter()


@oauth_router.get("/google/url")
def get_google_oauth_redirect_url():
    uri = generate_google_oauth_redirect_uri()
    return RedirectResponse(url=uri, status_code=status.HTTP_302_FOUND)


@oauth_router.post("/google/callback")
async def handle_google_oauth_callback(
    code: Annotated[str, Body()],
    state: Annotated[str, Body()],
):
    # Validate state for CSRF protection
    if state not in oauth_states:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")
    oauth_states.discard(state)

    google_token_url = settings.GOOGLE_TOKEN_URL

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
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to parse Google response: {e}")

            if "error" in result:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Unknown error"))

            id_token = result.get("id_token")
            access_token = result.get("access_token")
            if not id_token:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No id_token in response")

            user_data = jwt.decode(
                            id_token,
                            algorithms=["RS256"],
                            options={"verify_signature": False},
                        )
    return {
        "user": user_data,
        "access_token": access_token,
    }
