import pytest
from pydantic import ValidationError
from domain.events import EventItem


def test_event_item_valid():
    """Verify that a valid EventItem is correctly constructed."""
    event = EventItem(
        ms_type="user_action",
        event="login",
        correlation_id="corr-123"
    )
    assert event.ms_type == "user_action"
    assert event.event == "login"
    assert event.correlation_id == "corr-123"


def test_event_item_defaults():
    """Verify that correlation_id defaults to None if not provided."""
    event = EventItem(
        ms_type="system",
        event="startup"
    )
    assert event.ms_type == "system"
    assert event.event == "startup"
    assert event.correlation_id is None


def test_event_item_missing_required():
    """Verify that missing required fields raises a ValidationError."""
    with pytest.raises(ValidationError):
        # Missing event
        EventItem(ms_type="user_action")

    with pytest.raises(ValidationError):
        # Missing ms_type
        EventItem(event="login")


def test_event_item_model_dump():
    """Verify serialization to dictionary format."""
    event = EventItem(
        ms_type="user_action",
        event="login",
        correlation_id="corr-123"
    )
    dumped = event.model_dump()
    assert dumped == {
        "ms_type": "user_action",
        "event": "login",
        "correlation_id": "corr-123"
    }
