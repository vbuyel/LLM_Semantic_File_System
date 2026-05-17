"""
Unit tests for src.vector_db.adapters.database (DataBase class).
We mock psycopg and SentenceTransformer to avoid real DB/model connections.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("DOCS_POSTGRESQL_USERNAME", "test_user")
    monkeypatch.setenv("DOCS_POSTGRESQL_PASSWORD", "test_pass")
    monkeypatch.setenv("DOCS_POSTGRESQL_HOST", "localhost")
    monkeypatch.setenv("DOCS_POSTGRESQL_PORT", "5432")
    monkeypatch.setenv("DOCS_POSTGRESQL_DB", "test_db")
    monkeypatch.setenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


@pytest.fixture
def db_and_mocks(mock_env):
    """Create a DataBase instance with persistent mocks."""
    psycopg_patcher = patch("src.vector_db.adapters.database.psycopg")
    regvec_patcher = patch("src.vector_db.adapters.database.register_vector")
    st_patcher = patch("src.vector_db.adapters.database.SentenceTransformer")

    mock_psycopg = psycopg_patcher.start()
    regvec_patcher.start()
    mock_st = st_patcher.start()

    mock_conn = MagicMock()
    mock_psycopg.connect.return_value = mock_conn
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros(384, dtype=np.float32)
    mock_st.return_value = mock_model

    from src.vector_db.adapters.database import DataBase
    db = DataBase()

    yield db, mock_psycopg, mock_model

    st_patcher.stop()
    regvec_patcher.stop()
    psycopg_patcher.stop()


class TestVectorDBInit:
    def test_url_format(self, db_and_mocks):
        db, _, _ = db_and_mocks
        assert "test_user:test_pass@localhost:5432/test_db" in db.url

    def test_table_name(self, db_and_mocks):
        db, _, _ = db_and_mocks
        assert db.table == "documents"

    def test_vector_dim(self, db_and_mocks):
        db, _, _ = db_and_mocks
        assert db.vector_dim == 384

    def test_missing_env_raises(self, monkeypatch):
        for var in ["DOCS_POSTGRESQL_USERNAME", "DOCS_POSTGRESQL_PASSWORD",
                     "DOCS_POSTGRESQL_HOST", "DOCS_POSTGRESQL_PORT", "DOCS_POSTGRESQL_DB"]:
            monkeypatch.delenv(var, raising=False)
        with patch("src.vector_db.adapters.database.psycopg"), \
             patch("src.vector_db.adapters.database.register_vector"), \
             patch("src.vector_db.adapters.database.SentenceTransformer"):
            from src.vector_db.adapters.database import DataBase
            with pytest.raises(RuntimeError, match="Missing PostgreSQL env vars"):
                DataBase()


class TestSearchSimilar:
    def test_search_returns_rag_results(self, db_and_mocks):
        db, mock_psycopg, _ = db_and_mocks
        mock_conn = MagicMock()
        mock_conn.execute.return_value = [
            {"id": 1, "owner": "u", "file_name": "f.txt", "file_path": "/p", "text_chunk": "hello"},
        ]
        mock_psycopg.connect.return_value = mock_conn
        results = db.search_similar("guest", [0.0] * 384, limit=3)
        assert results.data is not None
        assert len(results.data) == 1

    def test_search_empty(self, db_and_mocks):
        db, mock_psycopg, _ = db_and_mocks
        mock_conn = MagicMock()
        mock_conn.execute.return_value = []
        mock_psycopg.connect.return_value = mock_conn
        results = db.search_similar("guest", [0.0] * 384)
        assert results.data == []


class TestUploadObject:
    def test_upload_no_text_raises(self, db_and_mocks):
        db, _, _ = db_and_mocks
        from src.vector_db.domain.domain import UploadObject
        obj = UploadObject(file_name="f", file_path="/p", text="")
        with pytest.raises(ValueError, match="No text provided"):
            db.upload_object(obj)

    def test_upload_success(self, db_and_mocks):
        db, mock_psycopg, _ = db_and_mocks
        mock_conn = MagicMock()
        mock_psycopg.connect.return_value = mock_conn
        from src.vector_db.domain.domain import UploadObject
        obj = UploadObject(file_name="f", file_path="/p", text="hello world test", owner="u")
        result = db.upload_object(obj)
        assert result.name == "f"
        assert result.chunks_added >= 1


class TestDeleteObject:
    def test_delete_with_owner(self, db_and_mocks):
        db, mock_psycopg, _ = db_and_mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn
        from src.vector_db.domain.domain import DeleteObject
        obj = DeleteObject(path="/p/f.txt", storage_type="gcs", owner="u")
        result = db.delete_object(obj)
        assert result.name == "f.txt"
        assert result.chunks_removed == 5

    def test_delete_without_owner(self, db_and_mocks):
        db, mock_psycopg, _ = db_and_mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn
        from src.vector_db.domain.domain import DeleteObject
        obj = DeleteObject(path="/p/f.txt", storage_type="gcs")
        result = db.delete_object(obj)
        assert result.name == "f.txt"
        assert result.chunks_removed == 3


class TestRenameObject:
    def test_rename(self, db_and_mocks):
        db, mock_psycopg, _ = db_and_mocks
        mock_conn = MagicMock()
        mock_psycopg.connect.return_value = mock_conn
        from src.vector_db.domain.domain import RenameObject
        obj = RenameObject(old_path="/old/f.txt", new_path="/new/g.txt", storage_type="gcs", owner="u")
        result = db.rename_object(obj)
        assert result.name == "g.txt"
