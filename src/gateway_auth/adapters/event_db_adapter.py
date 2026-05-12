import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class EventResponse(BaseModel):
    id: int
    owner: str
    event: str
    created_at: str


class EventsListResponse(BaseModel):
    events: list[EventResponse]
    total: int


class EventDBAdapter:
    def __init__(self):
        username = os.getenv("EVENT_POSTGRESQL_USERNAME")
        password = os.getenv("EVENT_POSTGRESQL_PASSWORD")
        host = os.getenv("EVENT_POSTGRESQL_HOST")
        port = os.getenv("EVENT_POSTGRESQL_PORT") or os.getenv("EVENT_POSTGREQSL_PORT")
        db_name = os.getenv("EVENT_POSTGRESQL_DB")

        missing = [
            name
            for name, value in (
                ("EVENT_POSTGRESQL_USERNAME", username),
                ("EVENT_POSTGRESQL_PASSWORD", password),
                ("EVENT_POSTGRESQL_HOST", host),
                ("EVENT_POSTGRESQL_PORT", port),
                ("EVENT_POSTGRESQL_DB", db_name),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing PostgreSQL env vars: " + ", ".join(missing)
            )

        self.url = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
        self.table = "events"

    def _get_connection(self):
        conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row)
        return conn

    def get_events_by_owner(
        self, owner: str, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        conn = self._get_connection()
        try:
            with conn.execute(
                f"""
                SELECT id, owner, event, created_at
                FROM {self.table}
                WHERE owner = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (owner, limit, offset),
            ) as cur:
                rows = cur.fetchall()
                return [
                    {
                        "id": row["id"],
                        "owner": row["owner"],
                        "event": row["event"],
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]
        finally:
            conn.close()

    def count_events_by_owner(self, owner: str) -> int:
        conn = self._get_connection()
        try:
            with conn.execute(
                f"SELECT COUNT(*) FROM {self.table} WHERE owner = %s",
                (owner,),
            ) as cur:
                return cur.fetchone()["count"]
        finally:
            conn.close()


_db: Optional[EventDBAdapter] = None


def get_event_db_adapter() -> EventDBAdapter:
    global _db
    if _db is None:
        _db = EventDBAdapter()
    return _db