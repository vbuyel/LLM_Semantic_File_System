import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv

from domain.domain import DeleteObject, DocMetadata, ObjectDeleted, ObjectRenamed, RAGResults, ObjectUploaded, RenameObject, UploadObject

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
                if object.owner and object.file_name:
                    conn.execute(
                        f"DELETE FROM {self.table} WHERE file_path = %s AND file_name = %s AND owner = %s",
                        (object.file_path, object.file_name, object.owner),
                    )
                elif object.owner:
                    conn.execute(
                        f"DELETE FROM {self.table} WHERE file_path = %s AND owner = %s",
                        (object.file_path, object.owner),
                    )
                elif object.file_name:
                    conn.execute(
                        f"DELETE FROM {self.table} WHERE file_path = %s AND file_name = %s",
                        (object.file_path, object.file_name),
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
        conn = self._get_connection()
        try:
            if object.owner and object.file_name:
                cur = conn.execute(
                    f"DELETE FROM {self.table} WHERE file_path = %s AND file_name = %s AND owner = %s",
                    (object.path, object.file_name, object.owner),
                )
            elif object.owner:
                cur = conn.execute(
                    f"DELETE FROM {self.table} WHERE file_path = %s AND owner = %s",
                    (object.path, object.owner),
                )
            elif object.file_name:
                cur = conn.execute(
                    f"DELETE FROM {self.table} WHERE file_path = %s AND file_name = %s",
                    (object.path, object.file_name),
                )
            else:
                cur = conn.execute(
                    f"DELETE FROM {self.table} WHERE file_path = %s",
                    (object.path,),
                )
            
            return ObjectDeleted(name=object.file_name or object.path, chunks_removed=cur.rowcount)
        finally:
            conn.close()


    def rename_object(self, object: RenameObject) -> ObjectRenamed:
        print("[DEBUG] Renaming object")
        conn = self._get_connection()
        try:
            if object.new_path:
                parts = object.new_path.rsplit("/", 1)
                new_dir = parts[0] + "/" if len(parts) > 1 else ""
                new_file_name = parts[-1] if parts[-1] else object.new_name
            else:
                new_dir = "root/"
                new_file_name = object.new_name

            old_file_name = object.old_file_name

            if object.owner and old_file_name:
                where_clause = "file_path = %s AND file_name = %s AND owner = %s"
                params = (object.old_path, old_file_name, object.owner)
            elif object.owner:
                where_clause = "file_path = %s AND owner = %s"
                params = (object.old_path, object.owner)
            elif old_file_name:
                where_clause = "file_path = %s AND file_name = %s"
                params = (object.old_path, old_file_name)
            else:
                where_clause = "file_path = %s"
                params = (object.old_path,)

            if object.new_path:
                conn.execute(
                    f'''
                    UPDATE {self.table}
                    SET file_path = %s, file_name = %s
                    WHERE {where_clause}
                    ''',
                    (new_dir, new_file_name, *params),
                )
            else:
                conn.execute(
                    f'''
                    UPDATE {self.table}
                    SET file_name = %s
                    WHERE {where_clause}
                    ''',
                    (new_file_name, *params),
                )
            return ObjectRenamed(name=new_file_name)
        finally:
            conn.close()
