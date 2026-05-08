import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv

from src.vector_db.domain.domain import DeleteObject, DocMetadata, ObjectDeleted, RAGResults, ObjectUploaded, UploadObject

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class DataBase:
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

        self._embedding_model = SentenceTransformer(
            os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )


    def _get_connection(self):
        conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row)
        register_vector(conn)
        return conn


    def _setup_database(self):
        conn = self._get_connection()
        try:
            conn.execute("""CREATE EXTENSION IF NOT EXISTS vector""")
        except Exception as e:
            print(f"Warning: Could not create vector extension: {e}")
        
        try:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table} (
                    id bigserial PRIMARY KEY,
                    owner TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    text_chunk TEXT,
                    embedding vector({self.vector_dim})
                )
            ''')
        except Exception as e:
            print(f"Warning creating table: {e}")
        
        try:
            conn.execute(f'''
                CREATE INDEX IF NOT EXISTS idx_embedding
                ON {self.table} USING hnsw (embedding vector_cosine_ops)
            ''')
        except Exception as e:
            print(f"Warning creating index: {e}")
        
        conn.close()


    def _convert_to_embedding(self, chunk: str) -> np.array:
        embedding = self._embedding_model.encode(chunk).tolist()
        return  np.array(embedding, dtype=np.float32)


    def search_similar(self, embedding: list[float], limit: int = 3) -> RAGResults:
        print("[DEBUG] Searching for simular text")
        conn = self._get_connection()
        try:
            result = conn.execute(f'''
                SELECT id, owner, file_name, file_path, text_chunk
                FROM {self.table}
                ORDER BY embedding <=> %s ASC
                LIMIT %s
                ''',
                (np.array(embedding, dtype=np.float32), limit),
            )
            return RAGResults(data=[DocMetadata(**row) for row in result])
        finally:
            conn.close()
    

    def upload_object(self, object: UploadObject) -> ObjectUploaded:
        print("[DEBUG] Uploading object")
        text = object.text
        if not text:
            raise ValueError("No text provided to upload")

        text = text.replace("\x00", "")
        chunks = object.divide_into_chunks(text, chunk_size=500, overlap=50)
        conn = self._get_connection()
        try:
            for chunk in chunks:
                embedding = self._convert_to_embedding(chunk)
                conn.execute(
                    f'''
                    INSERT INTO {self.table} (owner, file_name, file_path, text_chunk, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    ''',
                    (object.owner, object.file_name, object.file_path, chunk, embedding),
                )
            return ObjectUploaded(name=object.file_name, chunks_added=len(chunks))
        finally:
            conn.close()

    def delete_object(self, object: DeleteObject) -> ObjectDeleted:
        print("[DEBUG] Deleting object")
        conn = self._get_connection()
        try:
            result = conn.execute(
                f'''
                WITH deleted AS (
                    DELETE FROM {self.table}
                    WHERE file_path = %s AND owner = %s
                    RETURNING file_name
                )
                SELECT COUNT(*) as count, COALESCE(MAX(file_name), '') as file_name FROM deleted
                ''',
                (object.path, object.owner),
            )
            row = result.fetchone()
            chunks_removed = row["count"] if row else 0
            file_name = row["file_name"] if row and row["file_name"] else object.path.split("/")[-1]
            return ObjectDeleted(name=file_name, chunks_removed=chunks_removed)
        finally:
            conn.close()
