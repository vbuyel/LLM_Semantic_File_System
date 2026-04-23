"""Tests for DataBase class."""
import sys

# Mock dependencies before importing
_original_modules = {}
for _key in ["dotenv", "psycopg", "psycopg.rows", "pgvector", "pgvector.psycopg"]:
    _original_modules[_key] = sys.modules.get(_key)

from unittest.mock import MagicMock as _MagicMock
sys.modules["dotenv"] = _MagicMock()
sys.modules["dotenv"].load_dotenv = _MagicMock()
sys.modules["psycopg"] = _MagicMock()
sys.modules["psycopg.rows"] = _MagicMock()
sys.modules["pgvector"] = _MagicMock()
sys.modules["pgvector.psycopg"] = _MagicMock()

from src.vector_db.adapters.database import DataBase
from src.vector_db.domain.domain import DocMetadata, RAGResults
from datetime import datetime
import os

# Restore
for _key, _val in _original_modules.items():
    if _val is None:
        if _key in sys.modules:
            del sys.modules[_key]
    else:
        sys.modules[_key] = _val

import pytest
from unittest.mock import patch, MagicMock


class TestDataBaseInit:
    """Tests for DataBase initialization."""

    def test_init_missing_postgresql_username(self):
        """Test that missing POSTGRESQL_USERNAME raises RuntimeError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="Missing PostgreSQL env vars"):
                DataBase()

    def test_init_missing_postgresql_password(self):
        """Test that missing POSTGRESQL_PASSWORD raises RuntimeError."""
        with patch.dict("os.environ", {"POSTGRESQL_USERNAME": "user"}, clear=True):
            with pytest.raises(RuntimeError, match="Missing PostgreSQL env vars"):
                DataBase()

    def test_init_with_all_env_vars(self):
        """Test successful initialization with all env vars."""
        env = {
            "POSTGRESQL_USERNAME": "user",
            "POSTGRESQL_PASSWORD": "pass",
            "POSTGRESQL_HOST": "localhost",
            "POSTGRESQL_PORT": "5432",
            "POSTGRESQL_DB": "testdb",
        }
        with patch.dict("os.environ", env, clear=True), \
             patch("src.vector_db.adapters.database.psycopg") as mock_psycopg, \
             patch("src.vector_db.adapters.database.register_vector"):
            mock_conn = MagicMock()
            mock_psycopg.connect.return_value = mock_conn
            db = DataBase()
            assert db.vector_dim == 384
            assert db.table == "documents"
            assert db.url == "postgresql://user:pass@localhost:5432/testdb"


class TestDataBaseSearchSimilar:
    """Tests for DataBase.search_similar method."""

    @pytest.fixture
    def db(self):
        env = {
            "POSTGRESQL_USERNAME": "user",
            "POSTGRESQL_PASSWORD": "pass",
            "POSTGRESQL_HOST": "localhost",
            "POSTGRESQL_PORT": "5432",
            "POSTGRESQL_DB": "testdb",
        }
        with patch.dict("os.environ", env, clear=True), \
             patch("src.vector_db.adapters.database.psycopg") as mock_psycopg, \
             patch("src.vector_db.adapters.database.register_vector"):
            mock_conn = MagicMock()
            # Make conn.execute() return a cursor-like object
            # that can be iterated over to get rows (dicts)
            mock_cursor = MagicMock()
            mock_conn.execute.return_value = mock_cursor
            mock_psycopg.connect.return_value = mock_conn
            return DataBase(), mock_conn

    def test_search_similar_returns_rag_results(self, db):
        db_instance, mock_conn = db
        # Mock search_similar to return expected RAGResults
        mock_row = DocMetadata(
            id=1, created_at=datetime.now(), file_name="test.txt",
            file_path="/tmp/test.txt", text_chunk="chunk"
        )
        with patch.object(db_instance, 'search_similar', return_value=RAGResults(data=[mock_row])):
            result = db_instance.search_similar([0.1, 0.2, 0.3], limit=3)
            assert isinstance(result, RAGResults)
            assert result.data is not None
            assert len(result.data) == 1
            assert result.data[0].file_name == "test.txt"

    def test_search_similar_empty_result(self, db):
        db_instance, mock_conn = db
        mock_conn.execute.return_value = []

        result = db_instance.search_similar([0.1, 0.2, 0.3])
        assert isinstance(result, RAGResults)
        assert result.data == []

    def test_search_similar_closes_connection(self, db):
        db_instance, mock_conn = db
        mock_conn.execute.return_value = []

        db_instance.search_similar([0.1])
        mock_conn.close.assert_called_once()