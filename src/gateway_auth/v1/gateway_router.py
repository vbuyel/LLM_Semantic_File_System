import requests
from uuid import uuid4
from typing import Optional

from fastapi import status, APIRouter, Depends, File, Query, Request, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.gateway_auth.domain.file_ops import ListOfObjects, PathToGetObjects
from src.gateway_auth.domain.agent import ResponseToUser, UserRequest
from src.gateway_auth.domain.settings import settings


gateway_router = APIRouter()


def _get_headers(request: Request, headers: Optional[dict[str]] = {}) -> dict[str]:
    if auth := request.headers.get("Authorization"):
        headers["Authorization"] = auth
    if storage_source := request.headers.get("X-Storage-Source"):
        headers["X-Storage-Source"] = storage_source
    if auth_provider := request.headers.get("X-Auth-Provider"):
        headers["X-Auth-Provider"] = auth_provider
    owner = request.headers.get("X-Owner")
    if owner:
        headers["X-Owner"] = owner
    else:
        headers["X-Owner"] = "guest"
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    return headers


@gateway_router.post("/ai_agent")
def call_ai_agent(request: Request, user_request: UserRequest) -> ResponseToUser:
    """Calling AI Agent to get reponse from files or web search"""
    payload = {
        "text": user_request.text,
        "owner": "guest",
    }

    print(f"[DEBUG] Sending owner to agent: {payload.get('owner')}")
    try:
        response = requests.post(
            url=f"{settings.AGENT_SERVER}/get_response",
            json=payload,
            timeout=30,
        )
        if response.status_code != status.HTTP_200_OK:
            detail = response.json().get("detail", "Unknown error") if "application/json" in response.headers.get("content-type", "") else response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        
        return ResponseToUser(text=response.json().get("text", response.text))
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")


@gateway_router.get("/get_objects")
def get_objects_from_storage(request: Request, query: PathToGetObjects = Depends()) -> ListOfObjects:
    """Get list of available user's files and folders"""
    headers = _get_headers(request)
    
    print(f"[DEBUG] X-Owner: {headers.get("X-Owner")}")
    try:
        response = requests.get(
            url=f'{settings.FILE_OPS_SERVER}/get_all',
            params=query.model_dump(),
            headers=headers,
            timeout=90,
        )
        if response.status_code != status.HTTP_200_OK:
            detail = response.json().get("detail", "Unknown error") if "application/json" in response.headers.get("content-type", "") else response.text
            raise HTTPException(status_code=response.status_code, detail=detail)

        return ListOfObjects(**response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")


@gateway_router.post("/upload_object")
def upload_object_into_storage(request: Request, file: UploadFile = File(...)):
    """Upload user's file or object into Cloud"""
    headers = _get_headers(request)

    files = {"file": (file.filename, file.file, file.content_type)}

    print(f"[DEBUG] Sending owner to file_ops: {headers.get("owner")}")
    try:
        response = requests.post(
            url=f"{settings.FILE_OPS_SERVER}/upload",
            files=files,
            headers=headers,
            timeout=60,
        )
        if response.status_code != status.HTTP_200_OK:
            detail = response.json().get("detail", "Unknown error") if "application/json" in response.headers.get("content-type", "") else response.text
            raise HTTPException(status_code=response.status_code, detail=detail)

        return response.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")


@gateway_router.delete("/delete_object")
def delete_object_from_storage(request: Request, path: str = Query(...)):
    """Delete user's file or folder from Cloud"""
    headers = _get_headers(request)

    print(f"[DEBUG] Sending owner to file_ops: {headers.get("owner")}")
    try:
        response = requests.delete(
            url=f"{settings.FILE_OPS_SERVER}/delete",
            params={"path": path},
            headers=headers,
            timeout=30,
        )
        if response.status_code != status.HTTP_200_OK:
            detail = response.json().get("detail", "Unknown error") if "application/json" in response.headers.get("content-type", "") else response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        
        return response.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")


@gateway_router.put("/rename_object")
def rename_object_in_storage(request: Request, path: str = Query(...), new_name: str = Query(...)):
    """Rename a file in cloud storage"""
    headers = _get_headers(request)

    print(f"[DEBUG] Sending owner to file_ops: {headers.get("owner")}")
    try:
        response = requests.put(
            url=f"{settings.FILE_OPS_SERVER}/rename",
            params={"path": path, "new_name": new_name},
            headers=headers,
            timeout=30,
        )
        if response.status_code != status.HTTP_200_OK:
            detail = response.json().get("detail", "Unknown error") if "application/json" in response.headers.get("content-type", "") else response.text
            raise HTTPException(status_code=response.status_code, detail=detail)

        return response.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")


@gateway_router.get("/download_object")
def download_object_from_storage(request: Request, path: str = Query(...)):
    """Download a file from cloud storage and stream it back to the client."""
    headers = _get_headers(request)

    print(f"[DEBUG] Sending owner to file_ops: {headers.get("owner")}")
    try:
        response = requests.get(
            url=f"{settings.FILE_OPS_SERVER}/download",
            params={"path": path},
            headers=headers,
            timeout=120,
        )
        if response.status_code != status.HTTP_200_OK:
            detail = (
                response.json().get("detail", "Unknown error")
                if "application/json" in response.headers.get("content-type", "")
                else response.text
            )
            raise HTTPException(status_code=response.status_code, detail=detail)

        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/octet-stream"),
            headers={
                "Content-Disposition": response.headers.get(
                    "Content-Disposition", "attachment"
                ),
            },
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File service unavailable")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="File service timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Download failed: {str(e)}")
