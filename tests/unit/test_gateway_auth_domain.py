"""
Unit tests for gateway_auth domain models.
"""
import pytest
from src.gateway_auth.domain.agent import UserRequest, ResponseToUser
from src.gateway_auth.domain.events import EventItem, EventResponse
from src.gateway_auth.domain.file_ops import PathToGetObjects, FileItem, ListOfObjects

pytestmark = pytest.mark.unit


class TestUserRequest:
    def test_create(self):
        r = UserRequest(text="Find my document")
        assert r.text == "Find my document"

    def test_missing_text_raises(self):
        with pytest.raises(Exception):
            UserRequest()


class TestResponseToUser:
    def test_create(self):
        r = ResponseToUser(text="Here is the result")
        assert r.text == "Here is the result"


class TestGatewayEventItem:
    def test_create(self):
        e = EventItem(id=1, owner="o", event="e", created_at="t")
        assert e.id == 1

    def test_event_response(self):
        e = EventItem(id=1, owner="o", event="e", created_at="t")
        r = EventResponse(event=e)
        assert r.event.owner == "o"


class TestPathToGetObjects:
    def test_default_path(self):
        p = PathToGetObjects()
        assert p.path == "/"

    def test_custom_path(self):
        p = PathToGetObjects(path="/docs")
        assert p.path == "/docs"


class TestGatewayFileItem:
    def test_directory(self):
        f = FileItem(path="/d/", name="d", isDirectory=True)
        assert f.isDirectory is True
        assert f.size is None

    def test_file(self):
        f = FileItem(path="/f.txt", name="f.txt", isDirectory=False, size=42, modified="2026-01-01")
        assert f.size == 42


class TestListOfObjects:
    def test_create(self):
        files = [FileItem(path="/a", name="a", isDirectory=False)]
        lo = ListOfObjects(files=files, storage_type="gcs")
        assert len(lo.files) == 1
        assert lo.storage_type == "gcs"
