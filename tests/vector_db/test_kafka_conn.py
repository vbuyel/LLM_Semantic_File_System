"""Tests for vector_db kafka_conn module."""
import sys
import pytest
from unittest.mock import patch, MagicMock

# Mock all dependencies before importing
_original_modules = {}
for _key in ["dotenv", "psycopg", "psycopg.rows", "pgvector", "pgvector.psycopg",
             "sentence_transformers", "aiokafka", "aiokafka.AIOKafkaConsumer",
             "aiokafka.AIOKafkaProducer"]:
    _original_modules[_key] = sys.modules.get(_key)

# Create mocks
for _key in _original_modules:
    sys.modules[_key] = MagicMock()

sys.modules["aiokafka.AIOKafkaConsumer"] = MagicMock()
sys.modules["aiokafka.AIOKafkaProducer"] = MagicMock()

from src.vector_db.kafka_conn.main import (
    get_embedding_model, get_db, _embedding_model, _db
)

# Restore
for _key, _val in _original_modules.items():
    if _val is None:
        if _key in sys.modules:
            del sys.modules[_key]
    else:
        sys.modules[_key] = _val


class TestGetEmbeddingModel:
    def test_get_embedding_model_success(self):
        import src.vector_db.kafka_conn.main as kafka_mod
        _original = kafka_mod._embedding_model
        kafka_mod._embedding_model = None
        try:
            with patch("src.vector_db.kafka_conn.main.SentenceTransformer") as mock_st:
                mock_instance = MagicMock()
                mock_st.return_value = mock_instance
                with patch.dict("os.environ", {"EMBEDDING_MODEL": "test-model"}):
                    result = get_embedding_model()
                    assert result == mock_instance
                    mock_st.assert_called_once()
        finally:
            kafka_mod._embedding_model = _original

    def test_get_embedding_model_cached(self):
        import src.vector_db.kafka_conn.main as kafka_mod
        _original = kafka_mod._embedding_model
        mock_model = MagicMock()
        kafka_mod._embedding_model = mock_model
        try:
            result = get_embedding_model()
            assert result == mock_model
        finally:
            kafka_mod._embedding_model = _original

    def test_get_embedding_model_not_installed(self):
        # Mock SentenceTransformer as None to simulate not installed
        import src.vector_db.kafka_conn.main as kafka_mod
        _original = kafka_mod.SentenceTransformer
        kafka_mod.SentenceTransformer = None
        try:
            with pytest.raises(RuntimeError, match="sentence-transformers is not installed"):
                get_embedding_model()
        finally:
            kafka_mod.SentenceTransformer = _original


class TestGetDb:
    def test_get_db_success(self):
        with patch("src.vector_db.kafka_conn.main.DataBase") as mock_db_class:
            mock_instance = MagicMock()
            mock_db_class.return_value = mock_instance
            result = get_db()
            assert result == mock_instance

    def test_get_db_cached(self):
        mock_db = MagicMock()
        import src.vector_db.kafka_conn.main as kafka_mod
        kafka_mod._db = mock_db

        result = get_db()
        assert result == mock_db
