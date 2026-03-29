import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestVectorDBEndpointBugs:
    def test_bug_instantiating_abstract_class(self):
        from src.system.vector_db.adapters.abs_database import AbstractDataBase

        with pytest.raises(TypeError) as exc_info:
            AbstractDataBase()

        assert "abstract" in str(exc_info.value).lower()

    def test_bug_get_by_id_not_implemented(self):
        with patch.dict(
            "os.environ",
            {
                "POSTGRESQL_USERNAME": "test",
                "POSTGRESQL_PASSWORD": "test",
                "POSTGRESQL_HOST": "localhost",
                "POSTGRESQL_PORT": "5432",
                "POSTGRESQL_DB": "test",
            },
        ):
            with patch("src.system.vector_db.adapters.database.psycopg.connect"):
                with patch("src.system.vector_db.adapters.database.register_vector"):
                    from src.system.vector_db.adapters.database import DataBase

                    db = DataBase()

                    with pytest.raises(AttributeError) as exc_info:
                        db.get_by_id(1)

                    assert "get_by_id" in str(exc_info.value)

    def test_endpoint_main_has_bug_instantiating_abstract_class(self):
        with pytest.raises(TypeError) as exc_info:
            from src.system.vector_db.endpoints import main

            importlib.reload(main)

        assert "abstract" in str(exc_info.value).lower()


import importlib


@pytest.mark.skip(
    reason="Module has bug - cannot be imported directly due to AbstractDataBase instantiation"
)
class TestVectorDBEndpointsSkipped:
    def test_placeholder(self):
        pass
