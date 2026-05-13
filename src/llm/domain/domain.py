from pydantic import BaseModel
from typing import Optional


class RAGRequest(BaseModel):
    text: str

class RAGResponse(BaseModel):
    text: str

class SearchRequest(BaseModel):
    text: str
    owner: Optional[str] = None

class SearchResponse(BaseModel):
    text: str
