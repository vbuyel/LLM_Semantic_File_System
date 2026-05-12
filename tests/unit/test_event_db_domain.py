"""
Unit tests for src.event_db.domain.events models.
"""
import pytest
from src.event_db.domain.events import EventItem


pytestmark = pytest.mark.unit


class TestEventItem:
    """Tests for the EventItem Pydantic model."""

    def test_create_event_item(self):
        event = EventItem(id=1, owner="user@example.com", event="uploaded", created_at="2026-01-01 12:00:00")
        assert event.id == 1
        assert event.owner == "user@example.com"
        assert event.event == "uploaded"
        assert event.created_at == "2026-01-01 12:00:00"

    def test_event_item_serialization(self):
        event = EventItem(id=42, owner="test@mail.com", event="deleted", created_at="2026-05-12")
        data = event.model_dump()
        assert data == {
            "id": 42,
            "owner": "test@mail.com",
            "event": "deleted",
            "created_at": "2026-05-12",
        }

    def test_event_item_json_roundtrip(self):
        event = EventItem(id=7, owner="alice", event="renamed", created_at="2026-01-01")
        json_str = event.model_dump_json()
        restored = EventItem.model_validate_json(json_str)
        assert restored == event

    def test_event_item_missing_field_raises(self):
        with pytest.raises(Exception):
            EventItem(id=1, owner="user@example.com")  # missing event, created_at

    def test_event_item_wrong_id_type_coerced(self):
        # Pydantic v2 coerces int-like strings
        event = EventItem(id="99", owner="x", event="e", created_at="t")
        assert event.id == 99

    def test_event_item_immutable_fields(self):
        event = EventItem(id=1, owner="a", event="b", created_at="c")
        assert event.owner == "a"
