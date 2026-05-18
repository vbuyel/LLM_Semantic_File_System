from pydantic import BaseModel
from typing import Optional


class RAGRequest(BaseModel):
    text: str

class RAGResponse(BaseModel):
    text: str

class SearchRequest(BaseModel):
    text: str
    owner: str
    correlation_id: str

class SearchResponse(BaseModel):
    text: str
