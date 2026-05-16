from pydantic import BaseModel
from typing import List, Optional


class DocMetadata(BaseModel):
    id: int
    file_name: str
    file_path: str
    text_chunk: str

class RAGResults(BaseModel):
    data: List[DocMetadata] | None = None

class ObjectUploaded(BaseModel):
    name: str
    chunks_added: int = 0

class UploadObject(BaseModel):
    owner: str | None = None
    file_name: str
    file_path: str
    text: str | None = None
    file_size: int = 0

    def divide_into_chunks(self, text: str, chunk_size: int = 150, overlap: int = 20) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

class ObjectDeleted(BaseModel):
    name: str

class DeleteObject(BaseModel):
    path: str
    storage_type: str
    owner: str | None = None

class RenameObject(BaseModel):
    old_path: str
    new_path: str
    storage_type: str
    owner: str | None = None

class ObjectRenamed(BaseModel):
    name: str

class UploadEvent(BaseModel):
    owner: Optional[str] = None
    event: str
