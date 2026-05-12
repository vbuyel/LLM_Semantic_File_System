from pydantic import BaseModel


class EventItem(BaseModel):
    id: int
    owner: str
    event: str
    created_at: str
