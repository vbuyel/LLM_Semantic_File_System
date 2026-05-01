from fastapi import APIRouter, Depends, Request, HTTPException
import requests

from src.gateway_auth.domain.file_ops import ListOfObjects, PathToGetObjects
from src.gateway_auth.domain.agent import ResponseToUser, UserRequest
from src.gateway_auth.domain.settings import settings


gateway_router = APIRouter(prefix="/gateway")


@gateway_router.post("/ai_agent")
def call_ai_agent(request: UserRequest) -> ResponseToUser:
    """Calling AI Agent to get reponse from files or web search"""
    response = requests.post(
        url=f"{settings.AGENT_SERVER}/get_response",
        json=request.model_dump(),
    )
    return ResponseToUser(text=response.json().get("text", response.text))


@gateway_router.get("/get_objects")
def get_objects_from_storage(request: Request, query: PathToGetObjects = Depends()) -> ListOfObjects:
    """Get list of available user's files and folders"""
    headers = {}
    if auth := request.headers.get("Authorization"):
        headers["Authorization"] = auth
    if storage_source := request.headers.get("X-Storage-Source"):
        headers["X-Storage-Source"] = storage_source
    if auth_provider := request.headers.get("X-Auth-Provider"):
        headers["X-Auth-Provider"] = auth_provider

    try:
        response = requests.get(
            url=f'{settings.FILE_OPS_SERVER}/get_all',
            params=query.model_dump(),
            headers=headers,
            timeout=30,
        )
        if response.status_code != 200:
            detail = response.json().get("detail", "Unknown error") if "application/json" in response.headers.get("content-type", "") else response.text
            raise HTTPException(status_code=response.status_code, detail=detail)

        return ListOfObjects(**response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@gateway_router.post("/upload_object")
def upload_object_into_storage():
    """Upload user's file or object into Cloud"""
    pass


@gateway_router.delete("/delete_object")
def delete_object_from_storage():
    """Delete user's file or folder from Cloud"""
    pass
