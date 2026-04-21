import os
import psycopg
from pgvector.psycopg import register_vector
import numpy as np

from system.vector_db.adapters.repo_database import RepositoryDataBase


class DataBase(RepositoryDataBase):
    def __init__(self):
        self.url = f"postgresql://{os.getenv('POSTGRESQL_USERNAME')}:{os.getenv('POSTGRESQL_PASSWORD')}@{os.getenv('POSTGRESQL_HOST')}:{os.getenv('POSTGRESQL_PORT')}/{os.getenv('POSTGRESQL_DB')}"
        self.vector_dim = 384
        self.table = "documents"
        self._setup_database()


    def _get_connection(self):
        conn = psycopg.connect(self.url, autocommit=True)
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
                    text_chunk TEXT,
                    file_path TEXT,
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


    def search_similar(self, embedding: list[float], limit: int = 3) -> list[dict]:
        conn = self._get_connection()
        try:
            result = conn.execute(f'''
                SELECT *, embedding <=> %s AS distance
                FROM {self.table}
                ORDER BY distance ASC
                LIMIT %s
                ''',
                (np.array(embedding, dtype=np.float32), limit),
            )
            return [dict(row) for row in result]
        finally:
            conn.close()
