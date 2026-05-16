import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv

from src.vector_db.domain.domain import DeleteObject, DocMetadata, ObjectDeleted, ObjectRenamed, RAGResults, ObjectUploaded, RenameObject, UploadObject

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class DataBase:
    def __init__(self):
        username = os.getenv("DOCS_POSTGRESQL_USERNAME")
        password = os.getenv("DOCS_POSTGRESQL_PASSWORD")
        host = os.getenv("DOCS_POSTGRESQL_HOST")
        port = os.getenv("DOCS_POSTGRESQL_PORT")
        db_name = os.getenv("DOCS_POSTGRESQL_DB")
        
        missing = [
            name
            for name, value in (
                ("DOCS_POSTGRESQL_USERNAME", username),
                ("DOCS_POSTGRESQL_PASSWORD", password),
                ("DOCS_POSTGRESQL_HOST", host),
                ("DOCS_POSTGRESQL_PORT", port),
                ("DOCS_POSTGRESQL_DB", db_name),
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
            conn.execute(f'''
                ALTER TABLE {self.table} ADD COLUMN IF NOT EXISTS file_size BIGINT DEFAULT 0
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


    def _file_exists(self, file_path: str, file_name: str, file_size: int) -> bool:
        conn = self._get_connection()
        try:
            result = conn.execute(
                f"SELECT 1 FROM {self.table} WHERE file_path = %s AND file_name = %s AND file_size = %s LIMIT 1",
                (file_path, file_name, file_size),
            )
            return result.fetchone() is not None
        finally:
            conn.close()


    def _convert_to_embedding(self, chunk: str) -> np.array:
        embedding = self._embedding_model.encode(chunk).tolist()
        return  np.array(embedding, dtype=np.float32)


    def search_similar(self, owner: str, embedding: list[float], limit: int = 5) -> RAGResults:
        print("[DEBUG] Searching for simular text")
        conn = self._get_connection()
        try:
            result = conn.execute(f'''
                SELECT id, owner, file_name, file_path, text_chunk
                FROM {self.table}
                WHERE owner = %s
                ORDER BY embedding <=> %s ASC
                LIMIT %s
                ''',
                (owner, np.array(embedding, dtype=np.float32), limit),
            )
            return RAGResults(data=[DocMetadata(**row) for row in result])
        finally:
            conn.close()
    

    def upload_object(self, object: UploadObject, chunk_index: int = 0) -> ObjectUploaded:
        print("[DEBUG] Uploading object")
        text = object.text
        if not text:
            raise ValueError("No text provided to upload")

        if object.file_size and self._file_exists(object.file_path, object.file_name, object.file_size):
            print(f"[DEBUG] Skipping {object.file_path}: already indexed (size={object.file_size})")
            return ObjectUploaded(name=object.file_name, chunks_added=0)

        text = text.replace("\x00", "")
        chunks = object.divide_into_chunks(text)
        conn = self._get_connection()
        try:
            if chunk_index == 0:
                if object.owner:
                    conn.execute(
                        f"DELETE FROM {self.table} WHERE file_path = %s AND owner = %s",
                        (object.file_path, object.owner),
                    )
                else:
                    conn.execute(
                        f"DELETE FROM {self.table} WHERE file_path = %s",
                        (object.file_path,),
                    )

            for chunk in chunks:
                embedding = self._convert_to_embedding(chunk)
                conn.execute(
                    f'''
                    INSERT INTO {self.table} (owner, file_name, file_path, text_chunk, embedding, file_size)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    (object.owner, object.file_name, object.file_path, chunk, embedding, object.file_size),
                )
            return ObjectUploaded(name=object.file_name, chunks_added=len(chunks))
        finally:
            conn.close()


    def delete_object(self, object: DeleteObject) -> ObjectDeleted:
        print("[DEBUG] Deleting object")
        conn = self._get_connection()
        try:
            path = object.path
            if object.owner:
                conn.execute(
                    f"DELETE FROM {self.table} WHERE (file_path = %s OR file_path LIKE %s) AND owner = %s",
                    (path, f"{path}#chunk=%", object.owner),
                )
            else:
                conn.execute(
                    f"DELETE FROM {self.table} WHERE file_path = %s OR file_path LIKE %s",
                    (path, f"{path}#chunk=%"),
                )
            file_name = path.split("/")[-1]
            return ObjectDeleted(name=file_name)
        finally:
            conn.close()


    def rename_object(self, object: RenameObject) -> ObjectRenamed:
        print("[DEBUG] Renaming object")
        conn = self._get_connection()
        try:
            new_file_name = object.new_path.split("/")[-1]
            if object.owner:
                where_clause = "file_path = %s AND owner = %s"
                params = (object.old_path, object.owner)
            else:
                where_clause = "file_path = %s"
                params = (object.old_path,)
            
            conn.execute(
                f'''
                UPDATE {self.table}
                SET file_path = %s, file_name = %s
                WHERE {where_clause}
                ''',
                (object.new_path, new_file_name, *params),
            )
            return ObjectRenamed(name=new_file_name)
        finally:
            conn.close()
