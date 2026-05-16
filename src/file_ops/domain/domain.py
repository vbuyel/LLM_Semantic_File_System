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


class UploadObject(BaseModel):
    file_name: str
    file_path: str
    text: str
    owner: Optional[str] = None
    storage_type: str = "gcs"


class ObjectUploaded(BaseModel):
    file_name: str
    chunks_added: int = 0
    storage_type: str = "gcs"


class SendToKafka(BaseModel):
    action: str
    file_name: str
    file_path: str
    text: str = ""
    owner: Optional[str] = None
    storage_type: str = "unknown"
    chunk_index: int = 0
    file_size: int = 0
