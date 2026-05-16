import pytest
from src.event_db.domain.events import EventItem


pytestmark = pytest.mark.unit


class TestEventItem:
    def test_create_event_item(self):
        event = EventItem(ms_type="file_ops", event="uploaded")
        assert event.ms_type == "file_ops"
        assert event.event == "uploaded"

    def test_event_item_serialization(self):
        event = EventItem(ms_type="agent", event="deleted")
        data = event.model_dump()
        assert data == {"ms_type": "agent", "event": "deleted"}

    def test_event_item_json_roundtrip(self):
        event = EventItem(ms_type="file_ops", event="renamed")
        json_str = event.model_dump_json()
        restored = EventItem.model_validate_json(json_str)
        assert restored == event

    def test_event_item_missing_ms_type_raises(self):
        with pytest.raises(Exception):
            EventItem(event="uploaded")

    def test_event_item_missing_event_raises(self):
        with pytest.raises(Exception):
            EventItem(ms_type="file_ops")
