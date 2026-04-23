from pydantic import BaseModel
from typing import List
from datetime import datetime


class DocMetadata(BaseModel):
    id: int
    created_at: datetime
    file_name: str
    file_path: str
    text_chunk: str

class RAGResults(BaseModel):
    data: List[DocMetadata] | None = None
