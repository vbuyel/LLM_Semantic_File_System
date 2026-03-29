import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_env():
    test_env = {
        "POSTGRESQL_USERNAME": "test_user",
        "POSTGRESQL_PASSWORD": "test_pass",
        "POSTGRESQL_HOST": "localhost",
        "POSTGRESQL_PORT": "5432",
        "POSTGRESQL_DB": "test_db",
    }
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env
