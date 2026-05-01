from pydantic import BaseModel


class UserRequest(BaseModel):
    text: str

class ResponseToUser(BaseModel):
    text: str
