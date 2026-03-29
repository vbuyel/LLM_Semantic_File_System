import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_env():
    test_env = {
        "OPENROUTER_API_KEY": "test_key",
        "MODEL": "test_model",
        "LSFS_URL": "http://localhost",
    }
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env
