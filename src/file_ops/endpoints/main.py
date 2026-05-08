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
from typing import Optional
from src.file_ops.domain.domain import UploadResponse, ListFilesResponse, FileItem
from src.file_ops.adapters.gcs_ops import GCSOperations
from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations


app = FastAPI()
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
print(f"[DEBUG] Kafka topic: {os.getenv('REQUEST_TOPIC', 'NOT SET')}")
print(f"[DEBUG] Kafka bootstrap: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'NOT SET')}")


@app.get("/health")
def health_check():
    return {"status": "ok"}


async def _get_current_user(
    x_owner_email: Optional[str] = Header(None, alias="X-Owner-Email"),
    x_auth_provider: Optional[str] = Header(None, alias="X-Auth-Provider"),
    x_storage_source: Optional[str] = Header(None, alias="X-Storage-Source"),
    authorization: Optional[str] = Header(None),
):
    """
    Stub auth dependency.
    В реальности сюда подключишь JWT декодинг или проверку сессии.
    Возвращает: provider = "google" | "local", storage_source = "gcs" | "drive"
    """
    email = x_owner_email or None
    provider = x_auth_provider or "local"
    storage_source = x_storage_source or "gcs"
    token = authorization.replace("Bearer ", "") if authorization else None
    return {
        "owner": email,
        "provider": provider,
        "storage_source": storage_source,
        "token": token
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user=Depends(_get_current_user),
):
    # Сохраняем во временный файл
    temp_path = f"/tmp/{file.filename}"

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        storage_source = user.get("storage_source")
        owner = user.get("email")
        if storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google access token required for Drive upload")
            owner = user.get("email")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            result = drive_ops.upload_file(
                source_path=temp_path,
                owner=owner,
                file_name=file.filename,
                mime_type=file.content_type,
            )
        elif storage_source == "gcs":
            result = await gcs_ops.upload_file(
                source_path=temp_path,
                owner=owner,
                dest_name=file.filename,
                mime_type=file.content_type,
            )
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
    finally:
        # Cleanup
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
            files = drive_ops.list_files(path)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
        file_items = [FileItem(**f) for f in files] if files else []
        return ListFilesResponse(files=file_items, storage_type=storage_source)
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
    owner = user.get("owner")
    try:
        if storage_source == "gcs":
            await gcs_ops.delete_file(path, owner=owner)
        elif storage_source == "drive":
            if not user.get("token"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token required for Google Drive")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            drive_ops.delete_file(path, owner=user.get("owner"))
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported storage source: {storage_source}")
        return {"message": f"File {path} deleted from {storage_source}"}
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to delete file: {str(e)}")


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
