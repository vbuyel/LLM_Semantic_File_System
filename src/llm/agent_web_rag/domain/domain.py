from pydantic import BaseModel
from typing import List, Optional

class RAGRequest(BaseModel):
    text: str
    additional_data: Optional[str] = None

class RAGResponse(BaseModel):
    text: str

class DataForExtraction(BaseModel):
    text: str
    additional_data: List[str]

class DataExtracted(BaseModel):
    text: str

class SearchRequest(BaseModel):
    text: str
    file_path: Optional[str] = None

class SearchResponse(BaseModel):
    text: str
