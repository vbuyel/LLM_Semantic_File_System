"""
Run the server:
    uvicorn src.file_ops.endpoints.main:app --port 8002
"""
import os
import io
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from fastapi import status, FastAPI, UploadFile, File, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
from domain.domain import UploadResponse, ListFilesResponse, FileItem
from adapters.gcs_ops import GCSOperations
from adapters.google_drive_ops import GoogleDriveOperations
from adapters.kafka import KafkaOperations


kafka_ops = KafkaOperations()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await kafka_ops.start()
    yield
    await kafka_ops.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Инициализация один раз при старте
gcs_ops = GCSOperations(bucket_name=os.getenv("GCS_BUCKET_NAME"))
print(f"[DEBUG] GCS bucket: {os.getenv('GCS_BUCKET_NAME')}")
print(f"[DEBUG] Kafka topic: {os.getenv('REQUEST_TOPICS', 'NOT SET')}")
print(f"[DEBUG] Kafka bootstrap: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'NOT SET')}")


@app.get("/health")
def health_check():
    return {"status": "ok"}


async def _get_current_user(
    x_owner: Optional[str] = Header(None, alias="X-Owner"),
    x_auth_provider: Optional[str] = Header(None, alias="X-Auth-Provider"),
    x_storage_source: Optional[str] = Header(None, alias="X-Storage-Source"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
    authorization: Optional[str] = Header(None),
):
    """
    Stub auth dependency.
    В реальности сюда подключишь JWT декодинг или проверку сессии.
    Возвращает: provider = "google" | "local", storage_source = "gcs" | "drive"
    """
    email = x_owner or None
    provider = x_auth_provider or "local"
    storage_source = x_storage_source or "gcs"
    token = authorization.replace("Bearer ", "") if authorization else None
    print(f"[DEBUG] file_ops _get_current_user: owner='{email}', provider='{provider}', storage_source='{storage_source}'")
    return {
        "owner": email,
        "provider": provider,
        "storage_source": storage_source,
        "token": token,
        "correlation_id": x_correlation_id,
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user=Depends(_get_current_user),
):
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        storage_source = user.get("storage_source")
        owner = user.get("owner")
        if storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google access token required for Drive upload")
            owner = user.get("owner")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            result = await drive_ops.upload_file(
                source_path=temp_path,
                owner=owner,
                file_name=file.filename,
                mime_type=file.content_type,
            )
        elif storage_source == "gcs":
            result = await gcs_ops.upload_file(
                source_path=temp_path,
                dest_name=file.filename,
                mime_type=file.content_type,
                owner=user.get("owner"),
            )
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return UploadResponse(
        file_id=result["file_id"],
        file_name=file.filename,
        storage_type=result["storage_type"],
        url=result.get("url"),
        message=f"File uploaded to {result['storage_type']}",
    )


@app.get("/get_all", response_model=ListFilesResponse)
async def list_files(
    path: str = Query(default="/"),
    user=Depends(_get_current_user),
):
    storage_source = user.get("storage_source")
    try:
        if storage_source == "gcs":
            files = gcs_ops.list_files(path)
        elif storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token required for Google Drive")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            files = await drive_ops.list_files(owner=user.get("owner"), directory_path=path, correlation_id=user.get("correlation_id"))
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
        file_items = [FileItem(**f) for f in files] if files else []
        return ListFilesResponse(files=file_items, storage_type=storage_source)
    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to list files: {str(e)}")


@app.delete("/delete")
async def delete_file(
    path: str = Query(...),
    user=Depends(_get_current_user),
):
    storage_source = user["storage_source"]
    try:
        if storage_source == "gcs":
            await gcs_ops.delete_file(path, owner=user.get("owner"))
        elif storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token required for Google Drive")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            await drive_ops.delete_file(path, owner=user.get("owner"))
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
        return {"message": f"File {path} deleted from {storage_source}"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to delete file: {str(e)}")


@app.put("/rename")
async def rename_file(
    path: str = Query(..., description="Current file path or file_id"),
    new_name: str = Query(..., description="New file name"),
    user=Depends(_get_current_user),
):
    storage_source = user["storage_source"]
    owner = user.get("owner")
    print(f"[DEBUG] Rename request: storage={storage_source}, path={path}, new_name={new_name}")
    try:
        if storage_source == "gcs":
            result = await gcs_ops.rename_file(path, new_name, owner=user.get("owner"))
        elif storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token required for Google Drive")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            result = await drive_ops.rename_file(path, new_name, owner=owner)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
        return {"message": f"File renamed to {new_name}", **result}
    except HTTPException:
        raise
    except FileNotFoundError as e:
        print(f"[ERROR] FileNotFoundError: {e}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        print(f"[ERROR] ValueError: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        print(f"[ERROR] Exception: {type(e).__name__}: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to rename file: {str(e)}")


@app.get("/download")
async def download_file(
    path: str = Query(..., description="file_id for Drive, blob path for GCS"),
    user=Depends(_get_current_user),
):
    storage_source = user["storage_source"]
    try:
        if storage_source == "gcs":
            content, file_name, mime_type = gcs_ops.download_file(path)
        elif storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    "Google access token required for Drive download",
                )
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            content, file_name, mime_type = drive_ops.download_file(path)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")

        return StreamingResponse(
            io.BytesIO(content),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "Content-Length": str(len(content)),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to download file: {str(e)}")
