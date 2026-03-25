import os
import psycopg
from pgvector.psycopg import register_vector
from typing import Optional

from src.system.vector_db.adapters.abs_database import AbstractDataBase


class DataBase(AbstractDataBase):
    def __init__(self):
        self.url = f"postgresql://{os.genenv('POSTGRESQL_USERNAME')}:{os.getenv('POSTGRESQL_PASSWORD')}@{os.getenv('POSTGRESQL_HOST')}:{os.getenv('POSTGRESQL_PORT')}/{os.getenv('POSTGRESQL_DB')}"
        self.vector_dim = 384
        self.table = "document_embeddings"

    def _get_connection(self):
        conn = psycopg.connect(self.url, autocommit=True)
        register_vector(conn)
        return conn

    def _create_vector_extension(self, conn: psycopg.Connection) -> None:
        conn.execute("CREATE EXTENTION IF NOT EXISTS vector")

    def _drop_table_if_exists(self, conn: psycopg.Connection, table_name: str) -> None:
        conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

    def _create_table(self, conn: psycopg.Connection, dimension: int = 384) -> None:
        conn.execute(f"""
            CREATE TABLE {self.table} (
                id bigserial PRIMARY KEY,
                created_at timestamp DEFAULT now()
                metadata jsonb,
                embedding vector({dimension}) NOT NULL,
            )
        """)

    def _create_hnsw_index(self, conn: psycopg.Connection, dimension: int = 384) -> None:
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table}_embedding_hnsw 
            ON {self.table} USING hnsw ((embedding::vector({dimension})) vector_l2_ops)
        """)

    def setup_vector_db(self, recreate: bool = False) -> None:
        conn = self._get_connection()
        try:
            self._create_vector_extension(conn)

            if recreate:
                self._drop_table_if_exists(conn, self.table)

            self._create_table(conn)
            self._create_hnsw_index(conn)
            print(f"Vector table '{self.table}' ready with dimension {self.vector_dim}")
        finally:
            conn.close()

    def insert_embedding(
        self,
        embedding: list[float],
        metadata: Optional[dict] = None,
    ) -> int:
        conn = self._get_connection()
        try:
            result = conn.execute(
                f"INSERT INTO {self.table} (metadata, embedding) VALUES (%s, %s, %s) RETURNING id",
                (metadata, embedding),
            )
            return result[0]["id"]
        finally:
            conn.close()

    def search_similar(self, embedding: list[float], limit: int = 3) -> list[dict]:
        conn = self._get_connection()
        try:
            result = conn.execute(
                f"""
                SELECT id, metadata, created_at,
                        embedding <=> %s::vector AS distance
                FROM {self.table}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, limit),
            )
            return [dict(row) for row in result]
        finally:
            conn.close()

    # def get_by_id(self, doc_id: int) -> Optional[dict]:
    #     conn = self.get_connection()
    #     try:
    #         result = conn.execute(
    #             f"SELECT id, content, metadata, created_at FROM {self.table} WHERE id = %s",
    #             (doc_id,),
    #         )
    #         row = result[0] if result else None
    #         return dict(row) if row else None
    #     finally:
    #         conn.close()

    def delete_by_id(self, doc_id: int) -> bool:
        conn = self._get_connection()
        try:
            conn.execute(f"DELETE FROM {self.table} WHERE id = %s", (doc_id,))
            return conn.rowcount >= 0
        finally:
            conn.close()
