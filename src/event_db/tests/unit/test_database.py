import os
from unittest.mock import MagicMock, patch
import pytest
from adapters.database import DataBase
from domain.events import EventItem


def test_database_missing_env_vars():
    """Verify that DataBase raises RuntimeError if required environment variables are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError) as exc_info:
            DataBase()
        assert "Missing PostgreSQL env vars" in str(exc_info.value)
        assert "EVENT_POSTGRESQL_USERNAME" in str(exc_info.value)


def test_database_init_fallback_port():
    """Verify that DataBase successfully initializes using the typo fallback port."""
    env_mock = {
        "EVENT_POSTGRESQL_USERNAME": "user123",
        "EVENT_POSTGRESQL_PASSWORD": "password123",
        "EVENT_POSTGRESQL_HOST": "dbhost",
        "EVENT_POSTGREQSL_PORT": "5433",  # Typo fallback
        "EVENT_POSTGRESQL_DB": "testdb",
    }
    with patch.dict(os.environ, env_mock, clear=True):
        with patch.object(DataBase, "_setup_database") as mock_setup:
            db = DataBase()
            assert db.url == "postgresql://user123:password123@dbhost:5433/testdb"
            mock_setup.assert_called_once()


def test_database_setup_exception_handling():
    """Verify that _setup_database handles exceptions gracefully and closes connection."""
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("DB Connection Error")

    with patch.object(DataBase, "_get_connection", return_value=mock_conn):
        # Should not raise exception
        db = DataBase()
        mock_conn.close.assert_called_once()


def test_add_event_success():
    """Verify that add_event executes correct SQL and returns EventItem."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = ("user_action", "file_upload", "corr-123")

    # Set up mock cursor context manager
    mock_conn.execute.return_value.__enter__.return_value = mock_cur

    with patch.object(DataBase, "_setup_database"):
        db = DataBase()

        with patch.object(db, "_get_connection", return_value=mock_conn):
            event = db.add_event(
                owner="vlad",
                ms_type="user_action",
                event="file_upload",
                correlation_id="corr-123"
            )

            assert isinstance(event, EventItem)
            assert event.ms_type == "user_action"
            assert event.event == "file_upload"
            assert event.correlation_id == "corr-123"

            # Check execute arguments
            mock_conn.execute.assert_called_once()
            args, kwargs = mock_conn.execute.call_args
            assert args[1] == ("vlad", "user_action", "file_upload", "corr-123")
            mock_conn.close.assert_called_once()


def test_add_event_db_failure():
    """Verify that add_event propagates exceptions and closes connection."""
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("Database connection lost")

    with patch.object(DataBase, "_setup_database"):
        db = DataBase()

        with patch.object(db, "_get_connection", return_value=mock_conn):
            with pytest.raises(Exception) as exc_info:
                db.add_event("vlad", "user_action", "file_upload")

            assert "Database connection lost" in str(exc_info.value)
            mock_conn.close.assert_called_once()


def test_get_events_by_owner():
    """Verify get_events_by_owner returns expected EventItems without correlation_id."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [("user_action", "event_1")]
    mock_conn.execute.return_value.__enter__.return_value = mock_cur

    with patch.object(DataBase, "_setup_database"):
        db = DataBase()

        with patch.object(db, "_get_connection", return_value=mock_conn):
            events = db.get_events_by_owner(owner="vlad", ms_type="user_action")

            assert len(events) == 1
            assert events[0].ms_type == "user_action"
            assert events[0].event == "event_1"
            assert events[0].correlation_id is None

            mock_conn.execute.assert_called_once()
            args, kwargs = mock_conn.execute.call_args
            assert args[1] == ("vlad", "user_action")
            mock_conn.close.assert_called_once()


def test_get_events_by_owner_with_correlation_id():
    """Verify get_events_by_owner uses session filter when correlation_id is provided."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [("user_action", "session_event")]
    mock_conn.execute.return_value.__enter__.return_value = mock_cur

    with patch.object(DataBase, "_setup_database"):
        db = DataBase()

        with patch.object(db, "_get_connection", return_value=mock_conn):
            events = db.get_events_by_owner(
                owner="vlad",
                ms_type="user_action",
                correlation_id="corr-999",
            )
            assert len(events) == 1
            assert events[0].event == "session_event"
            mock_conn.execute.assert_called_once()
            args, kwargs = mock_conn.execute.call_args
            assert args[1] == ("vlad", "corr-999", "user_action")
            mock_conn.close.assert_called_once()


def test_cleanup_old_events_batching():
    """Verify that cleanup_old_events deletes in batches and stops when deleted count < batch_size."""
    mock_conn = MagicMock()
    mock_cur1 = MagicMock()
    mock_cur1.rowcount = 1000  # Equal to batch_size, so loop continues
    
    mock_cur2 = MagicMock()
    mock_cur2.rowcount = 450   # Less than batch_size, so loop terminates

    # Set up consecutive returns for the context manager
    mock_conn.execute.return_value.__enter__.side_effect = [mock_cur1, mock_cur2]

    with patch.object(DataBase, "_setup_database"):
        db = DataBase()

        with patch.object(db, "_get_connection", return_value=mock_conn):
            total_deleted = db.cleanup_old_events(retention_days=15, batch_size=1000)

            assert total_deleted == 1450
            assert mock_conn.execute.call_count == 2
            mock_conn.close.assert_called_once()
