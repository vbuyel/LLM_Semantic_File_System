"""
API Endpoints for file operations
Run: uvicorn src.llm.endpoints.main:app --port 8000
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from src.system.file_ops.local_ops import LocalFileOperations
from src.system.file_ops.google_drive_ops import GoogleDriveOperations
from src.system.file_ops.gcs_ops import GCSOperations

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_ROOT = Path("./storage")
STORAGE_ROOT.mkdir(exist_ok=True)

local_ops = LocalFileOperations(STORAGE_ROOT)
gdrive_ops = GoogleDriveOperations()
gcs_ops = GCSOperations()


class FileItem(BaseModel):
    name: str
    path: str
    size: int
    isDirectory: bool
    type: str
    modified: Optional[str] = None


class MoveRequest(BaseModel):
    sourcePath: str
    targetPath: str


class RenameRequest(BaseModel):
    path: str
    newName: str


class DeleteRequest(BaseModel):
    path: str


@app.get("/")
async def root():
    return {"message": "LLM Semantic File System API"}


@app.get("/files")
async def list_files(path: str = "/"):
    absolute_path = STORAGE_ROOT / path.lstrip("/")
    files = local_ops.list_directory(str(absolute_path))
    return files


@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...), path: str = "/"):
    absolute_path = STORAGE_ROOT / path.lstrip("/")
    result = await local_ops.upload_file(str(absolute_path), file)
    return result


@app.post("/files/move")
async def move_file(request: MoveRequest):
    result = local_ops.move_file(request.sourcePath, request.targetPath)
    return result


@app.post("/files/rename")
async def rename_file(request: RenameRequest):
    result = local_ops.rename_file(request.path, request.newName)
    return result


@app.delete("/files/delete")
async def delete_file(request: DeleteRequest):
    result = local_ops.delete_file(request.path)
    return result


@app.get("/files/download")
async def download_file(path: str):
    file_path = STORAGE_ROOT / path.lstrip("/")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=file_path.name)


@app.post("/cloud/google-drive/upload")
async def gdrive_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str = "root",
):
    task = background_tasks.add_task(gdrive_ops.upload_file, file, folder_id)
    return {"status": "upload started", "task_id": str(task)}


@app.get("/cloud/google-drive/files")
async def gdrive_list_files(folder_id: str = "root"):
    files = gdrive_ops.list_files(folder_id)
    return files


@app.post("/cloud/google-drive/move")
async def gdrive_move_file(file_id: str, target_folder_id: str):
    result = gdrive_ops.move_file(file_id, target_folder_id)
    return result


@app.post("/cloud/google-drive/delete")
async def gdrive_delete_file(file_id: str):
    result = gdrive_ops.delete_file(file_id)
    return result


@app.post("/cloud/gcs/upload")
async def gcs_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    bucket_name: str = None,
    destination: str = None,
):
    task = background_tasks.add_task(
        gcs_ops.upload_file, file, bucket_name, destination
    )
    return {"status": "upload started", "task_id": str(task)}


@app.get("/cloud/gcs/files")
async def gcs_list_files(bucket_name: str):
    files = gcs_ops.list_files(bucket_name)
    return files


@app.post("/cloud/gcs/move")
async def gcs_move_file(
    source_bucket: str, source_path: str, dest_bucket: str, dest_path: str
):
    result = gcs_ops.move_file(source_bucket, source_path, dest_bucket, dest_path)
    return result


@app.post("/cloud/gcs/delete")
async def gcs_delete_file(bucket_name: str, file_path: str):
    result = gcs_ops.delete_file(bucket_name, file_path)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
