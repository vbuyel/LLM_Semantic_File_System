import os
import psycopg
from pgvector.psycopg import register_vector
from typing import Optional


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))
TABLE_NAME = "document_embeddings"


def get_connection():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conn)
    return conn


def create_vector_extension(conn: psycopg.Connection) -> None:
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")


def drop_table_if_exists(conn: psycopg.Connection, table_name: str) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")


def create_table(conn: psycopg.Connection, dimension: int = VECTOR_DIMENSION) -> None:
    conn.execute(f"""
        CREATE TABLE {TABLE_NAME} (
            id bigserial PRIMARY KEY,
            content text NOT NULL,
            embedding vector({dimension}) NOT NULL,
            metadata jsonb,
            created_at timestamp DEFAULT now()
        )
    """)


def create_hnsw_index(
    conn: psycopg.Connection, dimension: int = VECTOR_DIMENSION
) -> None:
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_embedding_hnsw 
        ON {TABLE_NAME} USING hnsw ((embedding::vector({dimension})) vector_l2_ops)
    """)


def setup_vector_db(recreate: bool = False) -> None:
    conn = get_connection()
    try:
        create_vector_extension(conn)

        if recreate:
            drop_table_if_exists(conn, TABLE_NAME)

        create_table(conn)
        create_hnsw_index(conn)
        print(f"Vector table '{TABLE_NAME}' ready with dimension {VECTOR_DIMENSION}")
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vector database setup with pgvector")
    parser.add_argument(
        "--recreate", action="store_true", help="Drop and recreate the table"
    )
    args = parser.parse_args()

    setup_vector_db(recreate=args.recreate)
