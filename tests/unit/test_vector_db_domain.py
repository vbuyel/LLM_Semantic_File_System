"""
Unit tests for src.vector_db.domain.domain models.
"""
import pytest
from src.vector_db.domain.domain import (
    DocMetadata, RAGResults, ObjectUploaded, UploadObject,
    ObjectDeleted, DeleteObject, RenameObject, ObjectRenamed, UploadEvent,
)

pytestmark = pytest.mark.unit


class TestDocMetadata:
    def test_create(self):
        d = DocMetadata(id=1, file_name="f.txt", file_path="/p/f.txt", text_chunk="hello")
        assert d.id == 1
        assert d.text_chunk == "hello"


class TestRAGResults:
    def test_with_data(self):
        docs = [DocMetadata(id=1, file_name="f", file_path="/p", text_chunk="c")]
        r = RAGResults(data=docs)
        assert len(r.data) == 1

    def test_empty(self):
        r = RAGResults()
        assert r.data is None


class TestUploadObject:
    def test_divide_into_chunks_small_text(self):
        obj = UploadObject(file_name="f", file_path="/p", text="hello world")
        chunks = obj.divide_into_chunks("one two three four five", chunk_size=3, overlap=1)
        assert len(chunks) >= 1
        assert "one" in chunks[0]

    def test_divide_into_chunks_large_text(self):
        obj = UploadObject(file_name="f", file_path="/p")
        words = ["word"] * 1200
        text = " ".join(words)
        chunks = obj.divide_into_chunks(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 3

    def test_divide_empty_text(self):
        obj = UploadObject(file_name="f", file_path="/p")
        chunks = obj.divide_into_chunks("", chunk_size=500, overlap=50)
        assert chunks == []

    def test_optional_fields(self):
        obj = UploadObject(file_name="f", file_path="/p")
        assert obj.owner is None
        assert obj.text is None


class TestDeleteObject:
    def test_create(self):
        d = DeleteObject(path="/p/f.txt", storage_type="gcs", owner="u")
        assert d.path == "/p/f.txt"

    def test_optional_owner(self):
        d = DeleteObject(path="/p", storage_type="drive")
        assert d.owner is None


class TestRenameObject:
    def test_create(self):
        r = RenameObject(old_path="/old", new_path="/new", storage_type="gcs", owner="u")
        assert r.old_path == "/old"
        assert r.new_path == "/new"


class TestObjectUploaded:
    def test_create(self):
        o = ObjectUploaded(name="f.txt", chunks_added=5)
        assert o.chunks_added == 5


class TestObjectDeleted:
    def test_create(self):
        o = ObjectDeleted(name="f.txt")
        assert o.name == "f.txt"


class TestObjectRenamed:
    def test_create(self):
        o = ObjectRenamed(name="new.txt")
        assert o.name == "new.txt"


class TestUploadEvent:
    def test_create(self):
        e = UploadEvent(owner="u", event="uploaded")
        assert e.event == "uploaded"

    def test_optional_owner(self):
        e = UploadEvent(event="deleted")
        assert e.owner is None
