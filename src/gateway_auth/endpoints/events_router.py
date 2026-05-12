from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.gateway_auth.adapters.event_db_adapter import get_event_db_adapter


router = APIRouter(prefix="/events")


class EventItem(BaseModel):
    id: int
    owner: str
    event: str
    created_at: str


class EventsResponse(BaseModel):
    events: list[EventItem]
    total: int


@router.get("/user/{owner}", response_model=EventsResponse)
def get_user_events(
    owner: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    adapter = get_event_db_adapter()
    events = adapter.get_events_by_owner(owner=owner, limit=limit, offset=offset)
    total = adapter.count_events_by_owner(owner)
    return EventsResponse(
        events=[EventItem(**e) for e in events],
        total=total,
    )