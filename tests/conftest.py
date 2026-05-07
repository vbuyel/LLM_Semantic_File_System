"""
Test configuration and fixtures for integration tests.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_kafka_consumer():
    consumer = MagicMock()
    consumer.start = MagicMock()
    consumer.stop = MagicMock()
    return consumer


@pytest.fixture
def mock_kafka_producer():
    producer = MagicMock()
    producer.start = MagicMock()
    producer.stop = MagicMock()
    producer.send_and_wait = MagicMock(return_value=MagicMock())
    return producer


@pytest.fixture
def mock_vector_db():
    db = MagicMock()
    db.search_similar = MagicMock(return_value=MagicMock(data=[]))
    db.upload_object = MagicMock(return_value=MagicMock(name="test.txt", chunks_added=1))
    return db


@pytest.fixture
def mock_file_ops_response():
    return {
        "file_id": "test-file-id",
        "file_name": "test.txt",
        "storage_type": "gcs",
        "url": "https://storage.example.com/test.txt",
        "message": "File uploaded to gcs"
    }


@pytest.fixture
def sample_file_content():
    return b"This is a test file content for integration testing."


@pytest.fixture
def test_headers():
    return {
        "X-Owner-Email": "test@example.com",
        "X-Auth-Provider": "local",
        "X-Storage-Source": "gcs",
        "Authorization": "Bearer test-token"
    }


@pytest.fixture
def kafka_test_message():
    return {
        "correlation_id": "test-correlation-id",
        "reply_topic": "service.replies",
        "payload": {
            "action": "search",
            "text": "test search query",
            "owner": "test@example.com",
            "limit": 3
        }
    }


@pytest.fixture
def kafka_upload_message():
    return {
        "correlation_id": "test-correlation-id",
        "reply_topic": "service.replies",
        "payload": {
            "action": "upload",
            "file_name": "test.txt",
            "file_path": "/test.txt",
            "text": "This is test content to upload to vector database.",
            "owner": "test@example.com"
        }
    }
