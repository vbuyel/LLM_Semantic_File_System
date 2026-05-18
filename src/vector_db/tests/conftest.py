import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add the src/vector_db directory to sys.path so modules can be imported directly
vector_db_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(vector_db_dir))

# Mock sentence_transformers to avoid downloading/loading PyTorch during tests
sys.modules["sentence_transformers"] = MagicMock()

# Mock environment variables to avoid reading the real .env file and causing side effects
os.environ["DOCS_POSTGRESQL_USERNAME"] = "mock_user"
os.environ["DOCS_POSTGRESQL_PASSWORD"] = "mock_pass"
os.environ["DOCS_POSTGRESQL_HOST"] = "mock_host"
os.environ["DOCS_POSTGRESQL_PORT"] = "5432"
os.environ["DOCS_POSTGRESQL_DB"] = "mock_db"
os.environ["BROKER_HOSTS"] = "localhost:9092"
os.environ["REQUEST_TOPICS"] = "mock-request-topic"
os.environ["REPLY_EVENT_TOPIC"] = "mock-event-topic"
os.environ["EMBEDDING_MODEL"] = "sentence-transformers/all-MiniLM-L6-v2"
