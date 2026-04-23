import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
import numpy as np
from dotenv import load_dotenv

from src.vector_db.adapters.repo_database import RepositoryDataBase
from src.vector_db.domain.domain import DocMetadata, RAGResults

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class DataBase(RepositoryDataBase):
    def __init__(self):
        username = os.getenv("POSTGRESQL_USERNAME")
        password = os.getenv("POSTGRESQL_PASSWORD")
        host = os.getenv("POSTGRESQL_HOST")
        port = os.getenv("POSTGRESQL_PORT") or os.getenv("POSTGREQSL_PORT")
        db_name = os.getenv("POSTGRESQL_DB")
        
        missing = [
            name
            for name, value in (
                ("POSTGRESQL_USERNAME", username),
                ("POSTGRESQL_PASSWORD", password),
                ("POSTGRESQL_HOST", host),
                ("POSTGRESQL_PORT", port),
                ("POSTGRESQL_DB", db_name),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing PostgreSQL env vars: " + ", ".join(missing)
            )

        self.url = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
        self.vector_dim = 384
        self.table = "documents"
        self._setup_database()


    def _get_connection(self):
        conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row)
        register_vector(conn)
        return conn


    def _setup_database(self):
        conn = self._get_connection()
        try:
            conn.execute("""CREATE EXTENSION IF NOT EXISTS vector""")

            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table} (
                    id bigserial PRIMARY KEY,
                    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
                    file_name TEXT,
                    file_path TEXT,
                    text_chunk TEXT,
                    embedding vector({self.vector_dim})
                )
            ''')

            conn.execute(f'''
                CREATE INDEX IF NOT EXISTS idx_embedding
                ON {self.table} USING hnsw (embedding vector_cosine_ops)
            ''')
        except Exception as e:
            print(f"Error setting up database: {e}")
        finally:
            conn.close()


    def search_similar(self, embedding: list[float], limit: int = 3) -> RAGResults:
        print("Searching for simular text")
        conn = self._get_connection()
        try:
            result = conn.execute(f'''
                SELECT id, created_at, file_name, file_path, text_chunk
                FROM {self.table}
                ORDER BY embedding <=> %s ASC
                LIMIT %s
                ''',
                (np.array(embedding, dtype=np.float32), limit),
            )
            print(f"Found text: {result}")
            return RAGResults(data=[DocMetadata(**row) for row in result])
        finally:
            conn.close()
