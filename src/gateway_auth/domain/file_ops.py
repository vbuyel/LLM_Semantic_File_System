from pydantic import BaseModel
from typing import Optional, List


class PathToGetObjects(BaseModel):
    path: str = "/"

class FileItem(BaseModel):
    path: str
    name: str
    isDirectory: bool
    size: Optional[int] = None
    modified: Optional[str] = None


class ListOfObjects(BaseModel):
    files: List[FileItem]
    storage_type: str
