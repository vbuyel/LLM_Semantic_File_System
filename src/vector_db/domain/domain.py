from pydantic import BaseModel
from typing import List


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

    def divide_into_chunks(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks
