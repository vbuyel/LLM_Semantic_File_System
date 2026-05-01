from fastapi import APIRouter
import requests

from src.gateway_auth.domain.agent import ResponseToUser, UserRequest
from src.gateway_auth.domain.settings import settings


gateway_router = APIRouter(prefix="/gateway")


@gateway_router.post("/ai_agent")
def call_ai_agent(request: UserRequest) -> ResponseToUser:
    response = requests.post(
        url=f"{settings.AGENT_SERVER}/get_response",
        json=request.model_dump(),
    )
    return ResponseToUser(text=response.json().get("text", response.text))


@gateway_router.post("/file_ops")
def call_file_operations():
    pass
