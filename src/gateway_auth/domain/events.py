from pydantic import BaseModel
from typing import Optional


class EventItem(BaseModel):
    ms_type: str
    event: str
    correlation_id: Optional[str] = None

