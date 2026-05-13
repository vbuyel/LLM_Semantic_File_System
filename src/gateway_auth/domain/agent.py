from pydantic import BaseModel
from typing import Optional


class UserRequest(BaseModel):
    text: str
    owner: Optional[str] = None

class ResponseToUser(BaseModel):
    text: str
