import pytest
from pydantic import ValidationError
from domain.domain import (
    DocMetadata,
    RAGResults,
    ObjectUploaded,
    UploadObject,
    ObjectDeleted,
    DeleteObject,
    RenameObject,
    ObjectRenamed,
    UploadEvent,
)


def test_doc_metadata_validation():
    # Valid
    doc = DocMetadata(id=1, file_name="test.txt", file_path="/path/test.txt", text_chunk="hello")
    assert doc.id == 1
    assert doc.file_name == "test.txt"

    # Invalid type
    with pytest.raises(ValidationError):
        DocMetadata(id="not-an-int", file_name="test.txt", file_path="/path/test.txt", text_chunk="hello")


def test_rag_results_validation():
    results = RAGResults(data=[])
    assert results.data == []

    doc = DocMetadata(id=1, file_name="test.txt", file_path="/path/test.txt", text_chunk="hello")
    results = RAGResults(data=[doc])
    assert len(results.data) == 1
    assert results.data[0].file_name == "test.txt"


def test_upload_object_divide_into_chunks_basic():
    uploader = UploadObject(file_name="test.txt", file_path="/path/test.txt")
    
    # Text with 10 words
    text = "one two three four five six seven eight nine ten"
    
    # 1. Normal chunking when text is smaller than chunk_size but larger than min_chunk_size
    chunks = uploader.divide_into_chunks(text, chunk_size=5, overlap=1, min_chunk_size=3)
    # i=0: words[0:5] = ["one", "two", "three", "four", "five"]. len=5. Added.
    # i=4: words[4:9] = ["five", "six", "seven", "eight", "nine"]. len=5. Added.
    # i=8: words[8:13] = ["nine", "ten"]. len=2. Since 2 < min_chunk_size (3), appends to chunks[-1].
    # So we expect 2 chunks
    assert len(chunks) == 2
    assert chunks[0] == "one two three four five"
    assert chunks[1] == "five six seven eight nine nine ten"


def test_upload_object_divide_into_chunks_short_text():
    uploader = UploadObject(file_name="test.txt", file_path="/path/test.txt")
    
    # Text is shorter than min_chunk_size
    text = "hello world"
    chunks = uploader.divide_into_chunks(text, chunk_size=5, overlap=1, min_chunk_size=3)
    # Only one iteration, chunks is empty initially, so it'll go to 'else' and append
    assert len(chunks) == 1
    assert chunks[0] == "hello world"


def test_upload_object_divide_into_chunks_empty():
    uploader = UploadObject(file_name="test.txt", file_path="/path/test.txt")
    chunks = uploader.divide_into_chunks("")
    assert chunks == []


def test_upload_object_divide_into_chunks_invalid_step():
    uploader = UploadObject(file_name="test.txt", file_path="/path/test.txt")
    
    # When chunk_size <= overlap, range step is 0 or negative, which raises ValueError in range()
    with pytest.raises(ValueError):
        uploader.divide_into_chunks("some long text to trigger chunking logic in the loop", chunk_size=5, overlap=5)


def test_delete_object_validation():
    # Valid
    obj = DeleteObject(path="/path/test.txt", storage_type="local", owner="user@gmail.com")
    assert obj.path == "/path/test.txt"
    assert obj.file_name == ""

    # Missing storage_type and owner should raise ValidationError
    with pytest.raises(ValidationError):
        DeleteObject(path="/path/test.txt")


def test_rename_object_validation():
    # Valid
    obj = RenameObject(
        old_path="/path/old.txt",
        new_path="/path/new.txt",
        storage_type="gcs",
    )
    assert obj.old_path == "/path/old.txt"
    assert obj.new_path == "/path/new.txt"
    assert obj.owner is None
