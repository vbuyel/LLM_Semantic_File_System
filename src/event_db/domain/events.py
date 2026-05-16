from pydantic import BaseModel


class EventItem(BaseModel):
    ms_type: str
    event: str
