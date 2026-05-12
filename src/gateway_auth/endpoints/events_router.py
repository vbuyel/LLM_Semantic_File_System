from fastapi import APIRouter, Query

from src.gateway_auth.domain.events import EventResponse


event_router = APIRouter(prefix="/events")


@event_router.get("/", response_model=EventResponse)
def get_user_event(owner: str = Query(...)):
    # Get latest user's event in event_db service
    event = ...
    return EventResponse(event=event)
