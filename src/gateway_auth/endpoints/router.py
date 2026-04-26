from fastapi import APIRouter, Body
from typing import Annotated
from fastapi.responses import RedirectResponse
import aiohttp
import jwt

from src.gateway_auth.adapters.oauth_google import generate_google_oauth_redirect_uri
from src.gateway_auth.domain.domain import Settings

settings = Settings()
router = APIRouter(prefix="/auth")


@router.get("/google/url")
def get_google_oauth_redirect_url():
    uri = generate_google_oauth_redirect_uri()
    return RedirectResponse(url=uri, status_code=302)


@router.post("/google/callback")
async def handle_google_oauth_callback(code: Annotated[str, Body(embed=True)]):
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
        }) as response:
            result = await response.json()
            print(f"GOOGLE TOKEN RESPONSE: {result}")
            id_token = result["id_token"]
            user_data = jwt.decode(
                            id_token,
                            algorithms=["RS256"],
                            options={"verify_signature": False},
                        )
    
    return {"user": user_data}
