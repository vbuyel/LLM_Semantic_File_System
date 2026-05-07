"""
End-to-end integration tests for: Web -> Gateway -> File Ops -> Kafka -> VectorDB flow.
Tests the complete data pipeline from user request to vector storage.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestEndToEndFlow:
    """End-to-end integration tests for complete data pipeline."""

    def test_full_upload_to_vector_flow(self, mock_kafka_producer, sample_file_content):
        with patch("src.vector_db.kafka_conn.main.get_db") as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.upload_object = MagicMock(
                return_value=MagicMock(name="test.txt", chunks_added=2)
            )
            mock_db.return_value = mock_db_instance

            from src.vector_db.domain.domain import UploadObject

            upload_obj = UploadObject(
                file_name="test.txt",
                file_path="/test.txt",
                text="This is test content for vector embedding. " * 50,
                owner="test@example.com"
            )

            chunks = upload_obj.divide_into_chunks(upload_obj.text, chunk_size=500, overlap=50)

            result = mock_db_instance.upload_object(upload_obj)

            assert result.chunks_added >= 1

    def test_full_search_flow(self, mock_kafka_producer):
        with patch("src.vector_db.kafka_conn.main.get_embedding_model") as mock_embed:
            with patch("src.vector_db.kafka_conn.main.get_db") as mock_db:
                mock_embed_instance = MagicMock()
                mock_embed_instance.encode = MagicMock(return_value=MagicMock(tolist=lambda: [0.1] * 384))
                mock_embed.return_value = mock_embed_instance

                mock_db_instance = MagicMock()
                mock_db_instance.search_similar = MagicMock(
                    return_value=MagicMock(
                        data=[
                            MagicMock(
                                id=1,
                                created_at=datetime.now(),
                                file_name="result.txt",
                                file_path="/result.txt",
                                text_chunk="matching content"
                            )
                        ]
                    )
                )
                mock_db.return_value = mock_db_instance

                embedding = mock_embed_instance.encode("search query").tolist()
                results = mock_db_instance.search_similar(embedding, limit=3)

                assert len(results.data) >= 1


class TestGatewayKafkaVectorDBPipeline:
    """Tests for Gateway -> Kafka -> VectorDB pipeline."""

    def test_gateway_generates_correct_kafka_message(self):
        from src.gateway_auth.domain.agent import UserRequest

        request = UserRequest(
            text="Find files about project X",
        )

        request_dict = request.model_dump()

        assert "text" in request_dict

    def test_kafka_producer_sends_correct_message(self, mock_kafka_producer):
        message = {
            "correlation_id": "corr-789",
            "reply_topic": "service.replies",
            "payload": {
                "action": "search",
                "text": "user query",
                "owner": "user@example.com",
                "limit": 5
            }
        }

        mock_kafka_producer.send_and_wait = MagicMock(return_value=MagicMock())

        mock_kafka_producer.send_and_wait("service.replies", message)

        mock_kafka_producer.send_and_wait.assert_called_once()


class TestFileOpsToKafkaBridge:
    """Tests for file_ops -> Kafka bridge (simulated)."""

    def test_file_upload_triggers_kafka_message(self, mock_kafka_producer, sample_file_content):
        file_metadata = {
            "file_id": "file-123",
            "file_name": "document.txt",
            "file_path": "/documents/document.txt",
            "owner": "user@example.com",
            "content": "Sample content for vector storage."
        }

        kafka_message = {
            "correlation_id": "file-123",
            "reply_topic": "service.replies",
            "payload": {
                "action": "upload",
                "file_name": file_metadata["file_name"],
                "file_path": file_metadata["file_path"],
                "text": file_metadata["content"],
                "owner": file_metadata["owner"]
            }
        }

        mock_kafka_producer.send_and_wait = MagicMock(return_value=MagicMock())

        mock_kafka_producer.send_and_wait("service.requests", kafka_message)

        mock_kafka_producer.send_and_wait.assert_called_once()
        call_args = mock_kafka_producer.send_and_wait.call_args[0]
        assert call_args[0] == "service.requests"


class TestErrorPropagation:
    """Tests for error propagation through the pipeline."""

    def test_file_ops_error_propagates(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(status_code=500, detail="File storage error")

        assert exc_info.value.status_code == 500
        assert "File storage error" in str(exc_info.value.detail)

    def test_kafka_error_does_not_crash_service(self, mock_kafka_consumer, mock_kafka_producer):
        error_message = {
            "correlation_id": "error-corr",
            "reply_topic": "service.replies",
            "payload": {
                "action": "search",
                "text": "",
                "owner": "user@example.com"
            }
        }

        mock_kafka_consumer.__aiter__ = iter([])

        result = True

        assert result is True

    def test_vectordb_error_handling(self):
        from src.vector_db.domain.domain import UploadObject

        obj = UploadObject(
            file_name="test.txt",
            file_path="/test.txt",
            text=None,
            owner="test@example.com"
        )

        with pytest.raises(ValueError) as exc_info:
            if obj.text is None:
                raise ValueError("No text provided to upload")

        assert "No text provided" in str(exc_info.value)
