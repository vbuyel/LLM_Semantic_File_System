from pydantic import BaseModel
from typing import Optional, List


class UploadResponse(BaseModel):
    file_id: str
    file_name: str
    storage_type: str  # "gcs" или "drive"
    url: Optional[str] = None
    message: str


class FileItem(BaseModel):
    path: str
    name: str
    isDirectory: bool
    size: Optional[int] = None
    modified: Optional[str] = None


class ListFilesResponse(BaseModel):
    files: List[FileItem]
    storage_type: str
