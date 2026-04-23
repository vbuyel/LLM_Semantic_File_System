import sys
import pytest
from unittest.mock import MagicMock

# Mock all problematic modules to allow imports
_mocks = {
    "openai": MagicMock(),
    "dotenv": MagicMock(),
    "langchain_community": MagicMock(),
    "langchain_community.tools": MagicMock(),
    "aiokafka": MagicMock(),
    "sentence_transformers": MagicMock(),
    "psycopg": MagicMock(),
    "pgvector": MagicMock(),
}

for _name, _mock in _mocks.items():
    sys.modules[_name] = _mock

# Now we can import things
from src.llm.adapters.agent import AgentResearcher
from src.llm.endpoints.main import app
from fastapi.testclient import TestClient

# Make them available for test files
pytest.AgentResearcher = AgentResearcher
pytest.app = app
pytest.TestClient = TestClient
