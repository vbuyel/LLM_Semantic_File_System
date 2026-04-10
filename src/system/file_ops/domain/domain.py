from pydantic import BaseModel
from typing import Optional


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
