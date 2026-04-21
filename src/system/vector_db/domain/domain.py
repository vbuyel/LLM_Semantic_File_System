from pydantic import BaseModel
from typing import List
from datetime import datetime


class FoundDocPart(BaseModel):
    id: int
    created_at: datetime
    file_name: str
    file_path: str
    text_chunk: str

class SearchResult(BaseModel):
    data: List[FoundDocPart] | None = None
