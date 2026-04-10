import os
import pytest
from unittest.mock import patch, MagicMock


TEST_ENV = {
    "POSTGRESQL_USERNAME": "test_user",
    "POSTGRESQL_PASSWORD": "test_pass",
    "POSTGRESQL_HOST": "localhost",
    "POSTGRESQL_PORT": "5432",
    "POSTGRESQL_DB": "test_vector_db",
}


@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(os.environ, TEST_ENV, clear=True):
        yield


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.insert_embedding.return_value = 1
    db.get_by_id.return_value = {
        "id": 1,
        "metadata": {"source": "test"},
        "created_at": "2026-01-01T00:00:00",
    }
    db.search_similar.return_value = [
        {
            "id": 1,
            "metadata": {"source": "test"},
            "created_at": "2026-01-01T00:00:00",
            "distance": 0.1,
        }
    ]
    db.delete_by_id.return_value = True
    db.setup_vector_db.return_value = None
    return db


@pytest.fixture
def mock_database_class(mock_db):
    with patch(
        "src.system.vector_db.endpoints.main.DataBase", return_value=mock_db
    ) as mock_cls:
        yield mock_cls
