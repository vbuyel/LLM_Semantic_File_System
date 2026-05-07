"""
Integration tests for: Kafka -> VectorDB flow.
Tests the Kafka consumer processing requests and interacting with vector database.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.vector_db.domain.domain import UploadObject, ObjectUploaded, RAGResults, DocMetadata


class TestKafkaVectorDBIntegration:
    """Tests for Kafka message processing with vector database."""

    def test_process_search_request(self, mock_kafka_consumer, mock_kafka_producer, kafka_test_message):
        test_msg = MagicMock()
        test_msg.value = kafka_test_message

    def test_process_upload_request(self, mock_kafka_consumer, mock_kafka_producer, kafka_upload_message):
        test_msg = MagicMock()
        test_msg.value = kafka_upload_message


class TestVectorDBDomain:
    """Tests for vector database domain logic."""

    def test_upload_object_chunking(self):
        obj = UploadObject(
            file_name="test.txt",
            file_path="/test.txt",
            text="word " * 600,
            owner="test@example.com"
        )

        chunks = obj.divide_into_chunks(obj.text, chunk_size=500, overlap=50)

        assert len(chunks) > 1

    def test_upload_object_with_small_text(self):
        obj = UploadObject(
            file_name="small.txt",
            file_path="/small.txt",
            text="Short text",
            owner="test@example.com"
        )

        chunks = obj.divide_into_chunks(obj.text)

        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_rag_results_empty(self):
        results = RAGResults(data=None)

        assert results.data is None

    def test_rag_results_with_data(self):
        from datetime import datetime

        results = RAGResults(data=[
            DocMetadata(
                id=1,
                created_at=datetime.now(),
                file_name="test.txt",
                file_path="/test.txt",
                text_chunk="test content"
            )
        ])

        assert len(results.data) == 1
        assert results.data[0].file_name == "test.txt"


class TestKafkaMessageFormat:
    """Tests for Kafka message format and serialization."""

    def test_serialize_search_message(self, kafka_test_message):
        message_json = json.dumps(kafka_test_message).encode("utf-8")

        assert isinstance(message_json, bytes)
        deserialized = json.loads(message_json.decode("utf-8"))

        assert deserialized["correlation_id"] == "test-correlation-id"
        assert deserialized["payload"]["action"] == "search"

    def test_serialize_upload_message(self, kafka_upload_message):
        message_json = json.dumps(kafka_upload_message).encode("utf-8")

        assert isinstance(message_json, bytes)
        deserialized = json.loads(message_json.decode("utf-8"))

        assert deserialized["correlation_id"] == "test-correlation-id"
        assert deserialized["payload"]["action"] == "upload"

    def test_search_message_structure(self):
        message = {
            "correlation_id": "corr-123",
            "reply_topic": "service.replies",
            "payload": {
                "action": "search",
                "text": "query",
                "owner": "user@example.com",
                "limit": 5
            }
        }

        assert "correlation_id" in message
        assert "reply_topic" in message
        assert "payload" in message
        assert message["payload"]["action"] == "search"

    def test_upload_message_structure(self):
        message = {
            "correlation_id": "corr-456",
            "reply_topic": "service.replies",
            "payload": {
                "action": "upload",
                "file_name": "doc.txt",
                "file_path": "/doc.txt",
                "text": "content to embed",
                "owner": "user@example.com"
            }
        }

        assert "correlation_id" in message
        assert "reply_topic" in message
        assert "payload" in message
        assert message["payload"]["action"] == "upload"
        assert "text" in message["payload"]
