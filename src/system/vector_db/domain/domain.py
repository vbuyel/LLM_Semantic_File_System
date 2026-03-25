from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    metadata: Optional[dict] = None
    embedding: list[float]


class DocumentResponse(BaseModel):
    id: int
    metadata: Optional[dict]
    created_at: datetime


class DocumentSearch(BaseModel):
    embedding: list[float]
    limit: int = 3


class SearchResult(BaseModel):
    id: int
    metadata: Optional[dict]
    created_at: datetime
    distance: float
