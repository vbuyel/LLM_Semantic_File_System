"""
Unit tests for src.event_db.adapters.database (DataBase class).
We mock psycopg to avoid real DB connections.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.event_db.domain.events import EventItem


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_env(monkeypatch):
    """Set the required environment variables."""
    monkeypatch.setenv("EVENT_POSTGRESQL_USERNAME", "test_user")
    monkeypatch.setenv("EVENT_POSTGRESQL_PASSWORD", "test_pass")
    monkeypatch.setenv("EVENT_POSTGRESQL_HOST", "localhost")
    monkeypatch.setenv("EVENT_POSTGRESQL_PORT", "5432")
    monkeypatch.setenv("EVENT_POSTGRESQL_DB", "test_db")


@pytest.fixture
def db_and_mock(mock_env):
    """Create a DataBase instance with psycopg permanently mocked."""
    patcher = patch("src.event_db.adapters.database.psycopg")
    mock_psycopg = patcher.start()

    # Default connection mock for _setup_database
    mock_conn = MagicMock()
    mock_psycopg.connect.return_value = mock_conn

    from src.event_db.adapters.database import DataBase
    db = DataBase()

    yield db, mock_psycopg

    patcher.stop()


class TestDataBaseInit:
    def test_url_format(self, db_and_mock):
        db, _ = db_and_mock
        assert db.url == "postgresql://test_user:test_pass@localhost:5432/test_db"

    def test_table_name(self, db_and_mock):
        db, _ = db_and_mock
        assert db.table == "events"

    def test_setup_database_called(self, db_and_mock):
        _, mock_psycopg = db_and_mock
        assert mock_psycopg.connect.called

    def test_missing_env_vars_raises(self, monkeypatch):
        monkeypatch.delenv("EVENT_POSTGRESQL_USERNAME", raising=False)
        monkeypatch.delenv("EVENT_POSTGRESQL_PASSWORD", raising=False)
        monkeypatch.delenv("EVENT_POSTGRESQL_HOST", raising=False)
        monkeypatch.delenv("EVENT_POSTGRESQL_PORT", raising=False)
        monkeypatch.delenv("EVENT_POSTGREQSL_PORT", raising=False)
        monkeypatch.delenv("EVENT_POSTGRESQL_DB", raising=False)
        with patch("src.event_db.adapters.database.psycopg"):
            from src.event_db.adapters.database import DataBase
            with pytest.raises(RuntimeError, match="Missing PostgreSQL env vars"):
                DataBase()


class TestAddEvent:
    def test_add_event_returns_event_item(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, "user@test.com", "uploaded", "2026-01-01")
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        result = db.add_event("user@test.com", "uploaded")
        assert isinstance(result, EventItem)
        assert result.owner == "user@test.com"
        assert result.event == "uploaded"

    def test_add_event_calls_insert(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, "owner", "evt", "ts")
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        db.add_event("owner", "evt")
        mock_conn.execute.assert_called_once()


class TestGetEventsByOwner:
    def test_get_events_returns_list(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, "owner1", "uploaded", "2026-01-01"),
            (2, "owner1", "deleted", "2026-01-02"),
        ]
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        results = db.get_events_by_owner("owner1", limit=10, offset=0)
        assert len(results) == 2
        assert all(isinstance(r, EventItem) for r in results)

    def test_get_events_empty_owner(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        results = db.get_events_by_owner("nobody")
        assert results == []

    def test_connection_closed_after_query(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        db.get_events_by_owner("test")
        mock_conn.close.assert_called_once()
