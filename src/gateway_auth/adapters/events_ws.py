import asyncio
from typing import Optional

from src.gateway_auth.adapters.connection_manager import ConnectionManager


manager = ConnectionManager()

_events_poll_task: Optional[asyncio.Task] = None


async def poll_events():
    adapter = get_event_db_adapter()
    while True:
        for owner in list(manager.active_connections.keys()):
            try:
                event = adapter.get_event_by_owner(owner)
                if event:
                    last_id = manager.last_event_ids.get(owner)

                    if last_id is None or event["id"] > last_id:
                        manager.last_event_ids[owner] = event["id"]
                        await manager.broadcast_to_owner(
                            owner,
                            {"type": "events", "data": event},
                        )
            except Exception:
                pass
        await asyncio.sleep(1)


def start_events_polling():
    global _events_poll_task
    if _events_poll_task is None:
        _events_poll_task = asyncio.create_task(poll_events())


def stop_events_polling():
    global _events_poll_task
    if _events_poll_task:
        _events_poll_task.cancel()
        _events_poll_task = None
