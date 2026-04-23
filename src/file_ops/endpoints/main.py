"""
Run the server:
    uvicorn src.file_ops.endpoints.main:app --port 8002
"""
import os
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from src.file_ops.domain.domain import UploadResponse
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
gcs_ops = GCSOperations(bucket_name="your-bucket-name")


async def _get_current_user(
    x_auth_provider: Optional[str] = Header(None, alias="X-Auth-Provider"),
    authorization: Optional[str] = Header(None),
):
    """
    Stub auth dependency.
    В реальности сюда подключишь JWT декодинг или проверку сессии.
    Возвращает: provider = "google" | "local"
    """
    provider = x_auth_provider or "local"
    token = authorization.replace("Bearer ", "") if authorization else None
    return {"provider": provider, "token": token}


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
        if user["provider"] == "google":
            # Google OAuth user -> Google Drive
            if not user.get("token"):
                raise HTTPException(401, "Google access token required for Drive upload")
            drive_ops = GoogleDriveOperations(access_token=user["token"])
            result = drive_ops.upload_file(
                source_path=temp_path,
                file_name=file.filename,
                mime_type=file.content_type,
            )
        else:
            # Local user -> Google Cloud Storage
            result = gcs_ops.upload_file(
                source_path=temp_path,
                destination_name=file.filename,
                mime_type=file.content_type,
            )
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
