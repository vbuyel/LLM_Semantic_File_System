from typing import Generator
import os
from pathlib import Path
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class DataBase:
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
        conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row)
        return conn


    def _setup_database(self):
        conn = self._get_connection()
        try:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table} (
                    id bigserial PRIMARY KEY,
                    owner TEXT NOT NULL,
                    event TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        except Exception as e:
            print(f"Warning creating table: {e}")
        finally:
            conn.close()


    def add_event(self, owner: str, event: str) -> None:
        """Add an event to the database."""
        print(f"[DEBUG] Adding event: owner={owner}, event={event}")
        conn = self._get_connection()
        try:
            conn.execute(
                f'''
                INSERT INTO {self.table} (owner, event)
                VALUES (%s, %s)
                ''',
                (owner, event),
            )
            print("[DEBUG] Event added successfully")
        finally:
            conn.close()

    def get_unread_events(self, owner: str, last_id: int = 0, timeout: float = 30.0) -> Generator[dict, None, None]:
        import time
        poll_interval = 0.5
        elapsed = 0.0
        
        while elapsed < timeout:
            conn = self._get_connection()
            try:
                conn.execute(
                    f'''SELECT id, event, created_at FROM {self.table} 
                        WHERE owner = %s AND id > %s 
                        ORDER BY id ASC LIMIT 100''',
                    (owner, last_id)
                )
                rows = conn.fetchall()
                
                for row in rows:
                    last_id = row['id']
                    yield {
                        'id': row['id'],
                        'event': row['event'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None
                    }
            finally:
                conn.close()
            
            if not rows:
                time.sleep(poll_interval)
                elapsed += poll_interval

    def get_events_by_owner(self, owner: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Get events for a specific owner."""
        conn = self._get_connection()
        try:
            with conn.execute(
                f'''
                SELECT id, owner, event, created_at
                FROM {self.table}
                WHERE owner = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                ''',
                (owner, limit, offset),
            ) as cur:
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
