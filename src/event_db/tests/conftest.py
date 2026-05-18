import os
import sys
from pathlib import Path
import pytest

# Add the event_db directory to the sys.path so modules can be imported directly
event_db_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(event_db_dir))

# Set up mock environment variables for the database and service configuration
os.environ["EVENT_POSTGRESQL_USERNAME"] = "test_user"
os.environ["EVENT_POSTGRESQL_PASSWORD"] = "test_pass"
os.environ["EVENT_POSTGRESQL_HOST"] = "localhost"
os.environ["EVENT_POSTGRESQL_PORT"] = "5432"
os.environ["EVENT_POSTGRESQL_DB"] = "test_db"
os.environ["EVENT_RETENTION_DAYS"] = "30"
os.environ["EVENT_CLEANUP_INTERVAL_SECONDS"] = "86400"
os.environ["BROKER_HOSTS"] = "localhost:9092"
os.environ["REQUEST_TOPICS"] = "send_event"

@pytest.fixture
def anyio_backend():
    return "asyncio"
