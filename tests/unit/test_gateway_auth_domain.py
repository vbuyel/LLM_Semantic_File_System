import pytest
from src.gateway_auth.domain.agent import UserRequest, ResponseToUser
from src.gateway_auth.domain.events import EventItem, get_event_display_text
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
        e = EventItem(ms_type="file_ops", event="uploaded")
        assert e.ms_type == "file_ops"
        assert e.event == "uploaded"

    def test_missing_ms_type_raises(self):
        with pytest.raises(Exception):
            EventItem(event="uploaded")

    def test_missing_event_raises(self):
        with pytest.raises(Exception):
            EventItem(ms_type="file_ops")


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


class TestGetEventDisplayText:
    def test_uploading_event(self):
        assert get_event_display_text("uploading") == "Uploading file to cloud storage..."

    def test_deleting_event(self):
        assert get_event_display_text("deleting") == "Deleting file from cloud storage..."

    def test_renaming_event(self):
        assert get_event_display_text("renaming") == "Renaming file in cloud storage..."

    def test_updating_event(self):
        assert get_event_display_text("updating") == "Updating file in cloud storage..."

    def test_search_event(self):
        assert get_event_display_text("search") == "Searching your files..."

    def test_legacy_upload_event(self):
        assert get_event_display_text("upload") == "Uploading file to cloud storage..."

    def test_case_insensitive(self):
        assert get_event_display_text("UPLOADING") == "Uploading file to cloud storage..."

    def test_unknown_event(self):
        result = get_event_display_text("unknown_action")
        assert result == "Unknown_action"

    def test_none_event(self):
        assert get_event_display_text(None) == "Processing..."

    def test_empty_event(self):
        assert get_event_display_text("") == "Processing..."
