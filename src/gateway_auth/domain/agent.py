from pydantic import BaseModel


class UserRequest(BaseModel):
    text: str
    owner: str = ""

class ResponseToUser(BaseModel):
    text: str
