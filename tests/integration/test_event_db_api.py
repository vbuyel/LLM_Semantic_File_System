import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("EVENT_POSTGRESQL_USERNAME", "test")
    monkeypatch.setenv("EVENT_POSTGRESQL_PASSWORD", "test")
    monkeypatch.setenv("EVENT_POSTGRESQL_HOST", "localhost")
    monkeypatch.setenv("EVENT_POSTGRESQL_PORT", "5432")
    monkeypatch.setenv("EVENT_POSTGRESQL_DB", "testdb")
    monkeypatch.setenv("BROKER_HOSTS", "localhost:9092")
    monkeypatch.setenv("REQUEST_TOPICS", "test_events")


@pytest.fixture
def client(mock_env):
    with patch("src.event_db.v1.main.DataBase") as MockDB, \
         patch("src.event_db.v1.main.process_requests"):
        mock_db = MagicMock()
        MockDB.return_value = mock_db

        from src.event_db.v1.main import app, get_db
        import src.event_db.v1.main as mod
        mod._db = mock_db

        with TestClient(app) as c:
            yield c, mock_db


class TestEventDBHealth:
    def test_health(self, client):
        c, _ = client
        resp = c.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "event_db"


class TestGetUserEvents:
    def test_get_events(self, client):
        c, mock_db = client
        from src.event_db.domain.events import EventItem
        mock_db.get_events_by_owner.return_value = [
            EventItem(ms_type="file_ops", event="uploaded"),
        ]
        resp = c.get("/events/user/user@test.com?ms_type=file_ops")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert len(data["events"]) == 1

    def test_get_events_empty(self, client):
        c, mock_db = client
        mock_db.get_events_by_owner.return_value = []
        resp = c.get("/events/user/nobody?ms_type=file_ops")
        assert resp.status_code == 200
        assert resp.json()["events"] == []

    def test_get_events_with_pagination(self, client):
        c, mock_db = client
        mock_db.get_events_by_owner.return_value = []
        resp = c.get("/events/user/test?ms_type=file_ops&limit=10&offset=5")
        assert resp.status_code == 200
        mock_db.get_events_by_owner.assert_called_once_with("test", "file_ops", limit=10, offset=5)
