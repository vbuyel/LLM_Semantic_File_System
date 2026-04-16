from pydantic import BaseModel


class RAGRequest(BaseModel):
    text: str

class RAGResponse(BaseModel):
    text: str

class SearchRequest(BaseModel):
    text: str

class SearchResponse(BaseModel):
    text: str
