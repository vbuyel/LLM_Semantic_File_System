from fastapi import APIRouter

from src.gateway_auth.adapters.oauth_google import generate_google_oauth_redirect_url

router = APIRouter(prefix="/auth")


@router.get("/googl/url")
def get_google_oauth_redirect_url():
    uri = generate_google_oauth_redirect_url()
    return uri
