import os
import sys
from pathlib import Path
import pytest

# Add the src/file_ops directory to the sys.path so modules can be imported directly
file_ops_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(file_ops_dir))

# Set up mock environment variables for service configuration
os.environ["GCS_BUCKET_NAME"] = "test-bucket"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
os.environ["REQUEST_TOPICS"] = "service.requests"
os.environ["REPLY_TOPIC"] = "service.replies"
os.environ["EVENT_DB_TOPIC"] = "send_event"
os.environ["VECTOR_DB_URL"] = "http://localhost:8004"

@pytest.fixture
def anyio_backend():
    return "asyncio"
