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
    ]

    with patch("v1.main.get_db", return_value=mock_db):
        response = client.get(
            "/events/user/vlad",
            params={"ms_type": "action"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) == 1
        assert data["events"][0]["event"] == "click"

        mock_db.get_events_by_owner.assert_called_once_with("vlad", "action", None)


def test_get_user_events_with_correlation_id():
    """Verify GET /events/user/{owner} with correlation_id passes it to get_events_by_owner."""
    mock_db = MagicMock()
    mock_db.get_events_by_owner.return_value = [
        EventItem(ms_type="action", event="click"),
    ]

    with patch("v1.main.get_db", return_value=mock_db):
        response = client.get(
            "/events/user/vlad",
            params={"ms_type": "action", "correlation_id": "corr-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event"] == "click"

        mock_db.get_events_by_owner.assert_called_once_with("vlad", "action", "corr-123")


def test_get_user_events_missing_ms_type():
    """Verify GET /events/user/{owner} returns 422 Unprocessable Entity if ms_type query param is missing."""
    response = client.get("/events/user/vlad")
    assert response.status_code == 422
