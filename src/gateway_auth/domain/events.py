from pydantic import BaseModel


class EventItem(BaseModel):
    id: int
    owner: str
    event: str
    created_at: str


class EventResponse(BaseModel):
    event: EventItem


EVENT_DISPLAY_TEXT = {
    "uploading": "Uploading file to cloud storage...",
    "updating": "Updating file in cloud storage...",
    "deleting": "Deleting file from cloud storage...",
    "renaming": "Renaming file in cloud storage...",
    "upload": "Uploading file to cloud storage...",
    "update": "Updating file in cloud storage...",
    "delete": "Deleting file from cloud storage...",
    "rename": "Renaming file in cloud storage...",
    "search": "Searching your files...",
    "rag": "Analyzing your documents...",
    "agent": "AI is researching your files...",
    "ai_search": "AI is searching through your files...",
    "find in my files": "Searching your personal files...",
    "search my document": "Searching your documents...",
    "use rag": "Analyzing your documents...",
    "found": "Search complete",
    "uploaded": "File uploaded successfully",
    "updated": "File updated successfully",
    "deleted": "File deleted successfully",
    "renamed": "File renamed successfully",
}


def get_event_display_text(raw_event: str | None) -> str:
    if not raw_event:
        return "Processing..."
    
    if raw_event in EVENT_DISPLAY_TEXT:
        return EVENT_DISPLAY_TEXT[raw_event]
    
    lower_event = raw_event.lower()
    for key, value in EVENT_DISPLAY_TEXT.items():
        if key.lower() == lower_event:
            return value
    
    for key, value in EVENT_DISPLAY_TEXT.items():
        if key.lower() in lower_event or lower_event in key.lower():
            return value
    
    return raw_event.capitalize() if raw_event else "Processing..."

