import os
import pytest
from unittest.mock import MagicMock, patch, call, ANY
import numpy as np
from domain.domain import DeleteObject, RenameObject, UploadObject, DocMetadata, RAGResults


@pytest.fixture
def mock_db_dependencies():
    with patch("adapters.database.psycopg.connect") as mock_connect, \
         patch("adapters.database.register_vector") as mock_register, \
         patch("adapters.database.SentenceTransformer") as mock_transformer_class:
        
        # Setup mock connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        # Setup mock SentenceTransformer
        mock_transformer = mock_transformer_class.return_value
        # Mock encoding: return a mock whose tolist() returns 384 floats
        mock_emb = MagicMock()
        mock_emb.tolist.return_value = [0.5] * 384
        mock_transformer.encode.return_value = mock_emb
        
        yield mock_connect, mock_conn, mock_register, mock_transformer


def test_database_init_success(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    # Initialize DataBase
    from adapters.database import DataBase
    db = DataBase()
    
    assert db.url == "postgresql://mock_user:mock_pass@mock_host:5432/mock_db"
    assert db.vector_dim == 384
    assert db.table == "documents"
    
    # Verify setup database was called (creates extension, table, index)
    assert mock_conn.execute.call_count >= 4
    mock_conn.close.assert_called()


def test_database_init_missing_env_vars():
    # Remove some env vars
    with patch.dict(os.environ, {}, clear=True):
        from adapters.database import DataBase
        with pytest.raises(RuntimeError) as exc_info:
            DataBase()
        assert "Missing PostgreSQL env vars" in str(exc_info.value)


def test_file_exists(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    # Setup mock return value for fetchone
    mock_cursor = mock_conn.execute.return_value
    
    # Case 1: File exists
    mock_cursor.fetchone.return_value = (1,)
    exists = db._file_exists("path/to/file", "file.txt", 100)
    assert exists is True
    mock_conn.execute.assert_any_call(
        "SELECT 1 FROM documents WHERE file_path = %s AND file_name = %s AND file_size = %s LIMIT 1",
        ("path/to/file", "file.txt", 100)
    )
    
    # Case 2: File does not exist
    mock_cursor.fetchone.return_value = None
    exists = db._file_exists("path/to/file", "file.txt", 100)
    assert exists is False


def test_convert_to_embedding(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    embedding = db._convert_to_embedding("test chunk")
    assert isinstance(embedding, np.ndarray)
    assert embedding.dtype == np.float32
    assert embedding.shape == (384,)
    assert np.allclose(embedding, 0.5)
    mock_transformer.encode.assert_called_with("test chunk")


def test_search_similar_with_owner(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    # Setup mock rows returned by psycopg query
    mock_rows = [
        {"id": 1, "owner": "test@gmail.com", "file_name": "a.txt", "file_path": "dir/", "text_chunk": "hello"},
        {"id": 2, "owner": "test@gmail.com", "file_name": "b.txt", "file_path": "dir/", "text_chunk": "world"},
    ]
    mock_conn.execute.return_value = mock_rows
    
    query_emb = [0.1] * 384
    results = db.search_similar("test@gmail.com", query_emb, limit=2)
    
    assert isinstance(results, RAGResults)
    assert len(results.data) == 2
    assert results.data[0].file_name == "a.txt"
    assert results.data[1].text_chunk == "world"
    
    # Verify exact SQL sent with owner filter
    called_args = mock_conn.execute.call_args[0]
    sql = called_args[0]
    params = called_args[1]
    
    assert "WHERE owner = %s" in sql
    assert params[0] == "test@gmail.com"
    assert isinstance(params[1], np.ndarray)
    assert params[2] == 2


def test_search_similar_no_owner(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    mock_conn.execute.return_value = []
    
    query_emb = [0.1] * 384
    results = db.search_similar("guest", query_emb, limit=5)
    
    assert results.data == []
    
    # Verify SQL always includes owner filter
    called_args = mock_conn.execute.call_args[0]
    sql = called_args[0]
    params = called_args[1]
    
    assert "WHERE owner = %s" in sql
    assert params[0] == "guest"
    assert isinstance(params[1], np.ndarray)
    assert params[2] == 5


def test_upload_object_no_text(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    obj = UploadObject(owner="guest", file_name="a.txt", file_path="dir/", text=None)
    with pytest.raises(ValueError) as exc_info:
        db.upload_object(obj)
    assert "No text provided to upload" in str(exc_info.value)


def test_upload_object_already_indexed(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    # Mock _file_exists to return True
    db._file_exists = MagicMock(return_value=True)
    
    obj = UploadObject(owner="guest", file_name="a.txt", file_path="dir/", text="some content", file_size=123)
    result = db.upload_object(obj)
    
    assert result.name == "a.txt"
    assert result.chunks_added == 0
    db._file_exists.assert_called_with("dir/", "a.txt", 123)


def test_upload_object_success_new_file(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    # Mock file does not exist
    db._file_exists = MagicMock(return_value=False)
    
    # Check that null bytes are removed and chunking is triggered
    text_with_null_and_content = "Word1 Word2 Word3\x00 Word4 Word5"
    obj = UploadObject(
        owner="owner@gmail.com",
        file_name="doc.txt",
        file_path="docs/",
        text=text_with_null_and_content,
        file_size=100
    )
    
    # We patch the class method to guarantee multiple chunks and avoid modifying pydantic object attributes
    with patch("domain.domain.UploadObject.divide_into_chunks", return_value=["Word1 Word2", "Word3 Word4 Word5"]) as mock_chunk:
        result = db.upload_object(obj, chunk_index=0)
        
        # Verify chunking was called with text having null byte removed
        mock_chunk.assert_called_once_with("Word1 Word2 Word3 Word4 Word5")
        
        assert result.name == "doc.txt"
        assert result.chunks_added == 2
        
        # Verify old records were cleaned first (since chunk_index == 0)
        mock_conn.execute.assert_any_call(
            "DELETE FROM documents WHERE file_path = %s AND file_name = %s AND owner = %s",
            ("docs/", "doc.txt", "owner@gmail.com")
        )
        
        # Verify both chunks were inserted
        assert mock_conn.execute.call_count >= 3  # 1 for delete, 2 for insert
        mock_conn.execute.assert_any_call(
            "\n                    INSERT INTO documents (owner, file_name, file_path, text_chunk, embedding, file_size)\n                    VALUES (%s, %s, %s, %s, %s, %s)\n                    ",
            ("owner@gmail.com", "doc.txt", "docs/", "Word1 Word2", ANY, 100)
        )


def test_delete_object_owner_and_name(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    mock_cursor = mock_conn.execute.return_value
    mock_cursor.rowcount = 4
    
    obj = DeleteObject(path="dir/", file_name="file.txt", storage_type="local", owner="owner@gmail.com")
    result = db.delete_object(obj)
    
    assert result.name == "file.txt"
    assert result.chunks_removed == 4
    mock_conn.execute.assert_called_with(
        "DELETE FROM documents WHERE file_path = %s AND file_name = %s AND owner = %s",
        ("dir/", "file.txt", "owner@gmail.com")
    )


def test_delete_object_path_only(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    mock_cursor = mock_conn.execute.return_value
    mock_cursor.rowcount = 10
    
    obj = DeleteObject(path="dir/to/delete", file_name="", storage_type="local", owner="guest")
    result = db.delete_object(obj)
    
    assert result.name == "dir/to/delete"
    assert result.chunks_removed == 10
    mock_conn.execute.assert_called_with(
        "DELETE FROM documents WHERE file_path = %s AND owner = %s",
        ("dir/to/delete", "guest")
    )


def test_rename_object_full_path(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    obj = RenameObject(
        old_path="old_dir/",
        old_file_name="old.txt",
        new_path="new_dir/new.txt",
        new_name="ignored.txt",
        storage_type="local",
        owner="owner@gmail.com"
    )
    
    result = db.rename_object(obj)
    assert result.name == "new.txt"
    
    # Verify update query splits path into new_dir/ and new_file_name correctly
    mock_conn.execute.assert_called_with(
        "\n                    UPDATE documents\n                    SET file_path = %s, file_name = %s\n                    WHERE file_path = %s AND file_name = %s AND owner = %s\n                    ",
        ("new_dir/", "new.txt", "old_dir/", "old.txt", "owner@gmail.com")
    )


def test_rename_object_no_new_path(mock_db_dependencies):
    mock_connect, mock_conn, mock_register, mock_transformer = mock_db_dependencies
    
    from adapters.database import DataBase
    db = DataBase()
    
    obj = RenameObject(
        old_path="old_dir/",
        old_file_name="old.txt",
        new_path="",
        new_name="new_name.txt",
        storage_type="local",
        owner="guest"
    )
    
    result = db.rename_object(obj)
    assert result.name == "new_name.txt"
    
    # Verify update query when only new_name is provided
    mock_conn.execute.assert_called_with(
        "\n                    UPDATE documents\n                    SET file_name = %s\n                    WHERE file_path = %s AND file_name = %s AND owner = %s\n                    ",
        ("new_name.txt", "old_dir/", "old.txt", "guest")
    )
