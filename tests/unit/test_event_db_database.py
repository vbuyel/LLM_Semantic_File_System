import pytest
from unittest.mock import patch, MagicMock
from src.event_db.domain.events import EventItem


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("EVENT_POSTGRESQL_USERNAME", "test_user")
    monkeypatch.setenv("EVENT_POSTGRESQL_PASSWORD", "test_pass")
    monkeypatch.setenv("EVENT_POSTGRESQL_HOST", "localhost")
    monkeypatch.setenv("EVENT_POSTGRESQL_PORT", "5432")
    monkeypatch.setenv("EVENT_POSTGRESQL_DB", "test_db")


@pytest.fixture
def db_and_mock(mock_env):
    patcher = patch("src.event_db.adapters.database.psycopg")
    mock_psycopg = patcher.start()

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
        mock_cursor.fetchone.return_value = ("file_ops", "uploaded", "corr-123")
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        result = db.add_event("user@test.com", "file_ops", "uploaded")
        assert isinstance(result, EventItem)
        assert result.ms_type == "file_ops"
        assert result.event == "uploaded"
        assert result.correlation_id == "corr-123"

    def test_add_event_calls_insert(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("file_ops", "evt", None)
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        db.add_event("owner", "file_ops", "evt")
        mock_conn.execute.assert_called_once()


class TestGetEventsByOwner:
    def test_get_events_returns_list(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("file_ops", "uploaded"),
            ("file_ops", "deleted"),
        ]
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        results = db.get_events_by_owner("owner1", "file_ops", limit=10, offset=0)
        assert len(results) == 2
        assert all(isinstance(r, EventItem) for r in results)
        assert results[0].ms_type == "file_ops"
        assert results[0].event == "uploaded"

    def test_get_events_empty_owner(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        results = db.get_events_by_owner("nobody", "file_ops")
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

        db.get_events_by_owner("test", "file_ops")
        mock_conn.close.assert_called_once()


class TestCleanupOldEvents:
    def test_cleanup_deletes_old_events(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 100
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        result = db.cleanup_old_events(retention_days=30)
        assert result == 100

    def test_cleanup_batch_delete(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)

        call_count = 0
        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock_cursor.rowcount = 1000
            else:
                mock_cursor.rowcount = 500
            return mock_cursor

        mock_conn.execute.side_effect = execute_side_effect
        mock_psycopg.connect.return_value = mock_conn

        result = db.cleanup_old_events(retention_days=7, batch_size=1000)
        assert result == 1500
        assert call_count == 2

    def test_cleanup_stops_when_no_more_rows(self, db_and_mock):
        db, mock_psycopg = db_and_mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 500
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_cursor
        mock_psycopg.connect.return_value = mock_conn

        result = db.cleanup_old_events(retention_days=30, batch_size=1000)
        assert result == 500
