from pydantic import BaseModel
from typing import Optional


class Request(BaseModel):
    text: str
    file_path: Optional[str] = None


class Response(BaseModel):
    text: str
