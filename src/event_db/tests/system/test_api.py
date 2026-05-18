from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from v1.main import app, get_db
from domain.events import EventItem

client = TestClient(app)


def test_health_endpoint():
    """Verify the /health endpoint returns the correct status and alive flag."""
    with patch("v1.main._kafka_healthy", True):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "event_db",
            "consumer_alive": True
        }

    with patch("v1.main._kafka_healthy", False):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "event_db",
            "consumer_alive": False
        }


def test_get_user_events_without_correlation_id():
    """Verify GET /events/user/{owner} without correlation_id invokes get_events_by_owner."""
    mock_db = MagicMock()
    mock_db.get_events_by_owner.return_value = [
        EventItem(ms_type="action", event="click"),
        EventItem(ms_type="action", event="scroll"),
    ]

    with patch("v1.main.get_db", return_value=mock_db):
        response = client.get(
            "/events/user/vlad",
            params={"ms_type": "action", "limit": 10, "offset": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) == 2
        assert data["events"][0]["event"] == "click"
        assert data["events"][1]["event"] == "scroll"

        mock_db.get_events_by_owner.assert_called_once_with(
            "vlad", "action", limit=10, offset=2
        )
        mock_db.get_events_by_owner_or_session.assert_not_called()


def test_get_user_events_with_correlation_id():
    """Verify GET /events/user/{owner} with correlation_id invokes get_events_by_owner_or_session."""
    mock_db = MagicMock()
    mock_db.get_events_by_owner_or_session.return_value = [
        EventItem(ms_type="action", event="click"),
    ]

    with patch("v1.main.get_db", return_value=mock_db):
        response = client.get(
            "/events/user/vlad",
            params={"ms_type": "action", "limit": 5, "offset": 0, "correlation_id": "corr-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event"] == "click"

        mock_db.get_events_by_owner_or_session.assert_called_once_with(
            "vlad", "corr-123", "action", limit=5, offset=0
        )
        mock_db.get_events_by_owner.assert_not_called()


def test_get_user_events_missing_ms_type():
    """Verify GET /events/user/{owner} returns 422 Unprocessable Entity if ms_type query param is missing."""
    response = client.get("/events/user/vlad")
    assert response.status_code == 422
