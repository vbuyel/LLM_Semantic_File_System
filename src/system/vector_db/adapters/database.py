import os
import psycopg
from pgvector.psycopg import register_vector
import numpy as np

from src.system.vector_db.adapters.repo_database import RepositoryDataBase
from src.system.vector_db.domain.domain import FoundDocPart, SearchResult


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


    def search_similar(self, embedding: list[float], limit: int = 3) -> SearchResult:
        conn = self._get_connection()
        try:
            result = conn.execute(f'''
                SELECT (id, created_at, file_name, file_path, text_chunk), embedding <=> %s AS distance
                FROM {self.table}
                ORDER BY distance ASC
                LIMIT %s
                ''',
                (np.array(embedding, dtype=np.float32), limit),
            )
            return SearchResult(data=[FoundDocPart(**row) for row in result])
        finally:
            conn.close()
