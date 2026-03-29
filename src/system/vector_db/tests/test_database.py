import pytest
from unittest.mock import Mock, patch, MagicMock
from src.system.vector_db.adapters.database import DataBase
from src.system.vector_db.adapters.abs_database import AbstractDataBase
import psycopg


class TestDataBase:
    @pytest.fixture
    def mock_env(self):
        with patch.dict(
            "os.environ",
            {
                "POSTGRESQL_USERNAME": "test_user",
                "POSTGRESQL_PASSWORD": "test_pass",
                "POSTGRESQL_HOST": "localhost",
                "POSTGRESQL_PORT": "5432",
                "POSTGRESQL_DB": "test_db",
            },
        ):
            yield

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_database_initialization(self, mock_register, mock_connect, mock_env):
        db = DataBase()
        assert db.vector_dim == 384
        assert db.table == "document_embeddings"
        assert "postgresql://" in db.url

    def test_database_is_subclass_of_abstract(self):
        assert issubclass(DataBase, AbstractDataBase)

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_get_connection(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        db = DataBase()
        conn = db._get_connection()

        mock_connect.assert_called_once()
        mock_register.assert_called_once_with(mock_conn)

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_create_vector_extension(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        db = DataBase()
        db._create_vector_extension(mock_conn)

        mock_conn.execute.assert_called()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_drop_table_if_exists(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        db = DataBase()
        db._drop_table_if_exists(mock_conn, "test_table")

        mock_conn.execute.assert_called()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_create_table(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        db = DataBase()
        db._create_table(mock_conn)

        mock_conn.execute.assert_called()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_create_hnsw_index(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        db = DataBase()
        db._create_hnsw_index(mock_conn)

        mock_conn.execute.assert_called()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_setup_vector_db(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        db = DataBase()
        db.setup_vector_db(recreate=False)

        assert mock_conn.execute.call_count >= 3
        mock_conn.close.assert_called_once()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_insert_embedding(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.__getitem__ = Mock(return_value={"id": 1})
        mock_conn.execute.return_value = [mock_result]
        mock_connect.return_value = mock_conn

        db = DataBase()
        doc_id = db.insert_embedding([0.1, 0.2, 0.3], {"key": "value"})

        assert doc_id == {"id": 1}
        mock_conn.close.assert_called_once()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_search_similar(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_result = [
            {"id": 1, "metadata": {}, "created_at": "2024-01-01", "distance": 0.5},
            {"id": 2, "metadata": {}, "created_at": "2024-01-01", "distance": 0.6},
        ]
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        db = DataBase()
        results = db.search_similar([0.1, 0.2, 0.3], limit=3)

        assert len(results) == 2
        mock_conn.close.assert_called_once()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_delete_by_id(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_conn.rowcount = 1
        mock_connect.return_value = mock_conn

        db = DataBase()
        result = db.delete_by_id(1)

        assert result is True
        mock_conn.close.assert_called_once()

    @patch("src.system.vector_db.adapters.database.psycopg.connect")
    @patch("src.system.vector_db.adapters.database.register_vector")
    def test_delete_by_id_not_found(self, mock_register, mock_connect, mock_env):
        mock_conn = Mock()
        mock_conn.rowcount = 0
        mock_connect.return_value = mock_conn

        db = DataBase()
        result = db.delete_by_id(999)

        assert result is True


class TestAbstractDataBase:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            AbstractDataBase()
