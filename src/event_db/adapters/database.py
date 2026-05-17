import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from dotenv import load_dotenv

from src.event_db.domain.events import EventItem


load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class DataBase:
    url: str
    table: str

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
        self._setup_database()


    def _get_connection(self):
        conn = psycopg.connect(self.url, autocommit=True)
        return conn


    def _setup_database(self):
        conn = self._get_connection()
        try:
            conn.execute(sql.SQL('''
                CREATE TABLE IF NOT EXISTS {} (
                    id bigserial PRIMARY KEY,
                    owner TEXT NOT NULL,
                    ms_type TEXT NOT NULL DEFAULT '',
                    event TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''').format(sql.Identifier(self.table)))
            conn.execute(sql.SQL('''
                ALTER TABLE {} ADD COLUMN IF NOT EXISTS ms_type TEXT NOT NULL DEFAULT ''
            ''').format(sql.Identifier(self.table)))
            conn.execute(sql.SQL('''
                ALTER TABLE {} ADD COLUMN IF NOT EXISTS correlation_id TEXT
            ''').format(sql.Identifier(self.table)))
        except Exception as e:
            print(f"Warning creating table: {e}")
        finally:
            conn.close()


    def add_event(self, owner: str, ms_type: str, event: str, correlation_id: str | None = None) -> EventItem:
        print(f"[DEBUG] Database: add_event called with owner='{owner}', event='{event}', correlation_id='{correlation_id}'")
        conn = self._get_connection()
        try:
            print(f"[DEBUG] Database: Executing INSERT for owner='{owner}', event='{event}'")
            with conn.execute(
                sql.SQL('''
                INSERT INTO {} (owner, ms_type, event, correlation_id)
                VALUES (%s, %s, %s, %s)
                RETURNING ms_type, event, correlation_id
                ''').format(sql.Identifier(self.table)),
                (owner, ms_type, event, correlation_id),
            ) as cur:
                row: tuple[str, str, str | None] | None = cur.fetchone()
                print(f"[DEBUG] Database: Insert returned row: {row}")
                assert row is not None
                print(f"[DEBUG] Database: Event created")
                return EventItem(ms_type=row[0], event=row[1], correlation_id=row[2])
        finally:
            conn.close()


    def get_events_by_owner(self, owner: str, ms_type: str, limit: int = 1, offset: int = 0) -> list[EventItem]:
        print(f"[DEBUG] Database: get_events_by_owner called for owner='{owner}', limit={limit}, offset={offset}")
        conn = self._get_connection()
        try:
            with conn.execute(
                sql.SQL('''
                SELECT ms_type, event
                FROM {}
                WHERE owner = %s AND ms_type = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                ''').format(sql.Identifier(self.table)),
                (owner, ms_type, limit, offset),
            ) as cur:
                rows = cur.fetchall()
                print(f"[DEBUG] Database: Found {len(rows)} events for owner='{owner}'")
                return [
                    EventItem(ms_type=r[0], event=r[1])
                    for r in rows
                ]
        finally:
            conn.close()
