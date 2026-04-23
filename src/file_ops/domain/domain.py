from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    file_id: str
    file_name: str
    storage_type: str  # "gcs" или "drive"
    url: Optional[str] = None
    message: str
