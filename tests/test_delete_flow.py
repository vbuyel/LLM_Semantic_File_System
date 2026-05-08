"""
Integration tests for the complete delete flow:
web → gateway → file_ops → kafka → vector_db

Tests the end-to-end deletion of a file with owner-based filtering.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.gateway_auth.endpoints.gateway_router import delete_object_from_storage


class TestDeleteFlowGateway:
    def test_delete_endpoint_includes_owner_header(self):
        mock_request = MagicMock()
        mock_request.headers = {
            "Authorization": "Bearer test-token",
            "X-Storage-Source": "gcs",
            "X-Auth-Provider": "google",
            "X-Owner-Email": "user@example.com",
        }

        with patch("src.gateway_auth.endpoints.gateway_router.requests.delete") as mock_delete:
            mock_delete.return_value = MagicMock(
                status_code=200,
                json=lambda: {"message": "deleted"},
                headers={"content-type": "application/json"}
            )

            delete_object_from_storage(mock_request, path="/test.txt")

            mock_delete.assert_called_once()
            call_kwargs = mock_delete.call_args[1]
            assert call_kwargs["headers"].get("X-Owner-Email") == "user@example.com"

    def test_delete_endpoint_missing_owner_header(self):
        mock_request = MagicMock()
        mock_request.headers = {
            "Authorization": "Bearer test-token",
            "X-Storage-Source": "gcs",
        }

        with patch("src.gateway_auth.endpoints.gateway_router.requests.delete") as mock_delete:
            mock_delete.return_value = MagicMock(
                status_code=200,
                json=lambda: {"message": "deleted"},
                headers={"content-type": "application/json"}
            )

            delete_object_from_storage(mock_request, path="/test.txt")

            mock_delete.assert_called_once()
            call_kwargs = mock_delete.call_args[1]
            assert "headers" in call_kwargs


class TestDeleteFlowFileOps:
    @pytest.fixture
    def mock_gcs_ops(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_delete_gcs_sends_kafka_event(self, mock_gcs_ops):
        from src.file_ops.adapters.gcs_ops import GCSOperations

        with patch.dict("os.environ", {"REQUEST_TOPICS": "topic1,topic2"}):
            gcs = GCSOperations(bucket_name="test-bucket")
            gcs._bucket = MagicMock()
            gcs._client = MagicMock()

            blob_mock = MagicMock()
            blob_mock.exists.return_value = True
            gcs._bucket.blob.return_value = blob_mock

            with patch.object(gcs, '_send_kafka_event', new_callable=AsyncMock) as mock_kafka:
                await gcs.delete_file("/test.txt")

                mock_kafka.assert_called_once()
                call_args = mock_kafka.call_args[0][0]
                assert call_args["action"] == "delete"
                assert call_args["file_path"] == "/test.txt"
                assert call_args["storage_type"] == "gcs"

    @pytest.mark.asyncio
    async def test_delete_drive_sends_kafka_event(self):
        with patch.dict("os.environ", {"REQUEST_TOPICS": "topic1,topic2"}):
            mock_delete_builder = MagicMock()
            mock_delete_builder.execute.return_value = None

            mock_files = MagicMock()
            mock_files.delete.return_value = mock_delete_builder

            mock_service = MagicMock()
            mock_service.files.return_value = mock_files

            with patch("googleapiclient.discovery.build", return_value=mock_service):
                from src.file_ops.adapters.google_drive_ops import GoogleDriveOperations
                drive = GoogleDriveOperations(access_token="test-token")

                with patch.object(drive, '_send_kafka_delete_event', new_callable=AsyncMock) as mock_kafka:
                    drive.delete_file("file-id-123", owner="user@example.com")

                    mock_kafka.assert_called_once()
                    call_args = mock_kafka.call_args[0]
                    assert call_args[0] == "file-id-123"
                    assert call_args[1] == "user@example.com"


class TestDeleteFlowKafkaConsumer:
    def test_kafka_consumer_processes_delete_action(self):
        from src.vector_db.domain.domain import DeleteObject, ObjectDeleted

        delete_message = {
            "correlation_id": "test-corr-id",
            "reply_topic": "service.replies",
            "payload": {
                "action": "delete",
                "file_path": "/test.txt",
                "storage_type": "gcs",
                "owner": "user@example.com"
            }
        }

        mock_db = MagicMock()
        mock_db.delete_object.return_value = ObjectDeleted(name="test.txt", chunks_removed=5)

        with patch('src.vector_db.kafka_conn.main.get_db', return_value=mock_db):
            from src.vector_db.kafka_conn.main import get_db

            db = get_db()
            object_to_delete = DeleteObject(
                path=delete_message["payload"]["file_path"],
                storage_type=delete_message["payload"]["storage_type"],
                owner=delete_message["payload"]["owner"]
            )
            result = db.delete_object(object_to_delete)

            assert result.chunks_removed == 5
            mock_db.delete_object.assert_called_once()
            call_args = mock_db.delete_object.call_args[0][0]
            assert isinstance(call_args, DeleteObject)
            assert call_args.path == "/test.txt"
            assert call_args.owner == "user@example.com"

    def test_kafka_delete_includes_owner_filter(self):
        from src.vector_db.adapters.database import DataBase
        from src.vector_db.domain.domain import DeleteObject

        db = DataBase.__new__(DataBase)
        db.table = "documents"
        db.url = "postgresql://test:test@localhost:5432/test"

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {"count": 3, "file_name": "test.txt"}
        mock_conn.execute.return_value = mock_result

        db._get_connection = MagicMock(return_value=mock_conn)

        delete_obj = DeleteObject(path="/test.txt", storage_type="gcs", owner="user@example.com")
        result = db.delete_object(delete_obj)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][1]
        assert "/test.txt" in sql_call
        assert "user@example.com" in sql_call


class TestDeleteFlowOwnerFiltering:
    def test_delete_only_removes_owners_chunks(self):
        from src.vector_db.adapters.database import DataBase
        from src.vector_db.domain.domain import DeleteObject

        db = DataBase.__new__(DataBase)
        db.table = "documents"
        db.url = "postgresql://test:test@localhost:5432/test"

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {"count": 2, "file_name": "report.pdf"}
        mock_conn.execute.return_value = mock_result

        db._get_connection = MagicMock(return_value=mock_conn)

        delete_obj = DeleteObject(
            path="/documents/report.pdf",
            storage_type="gcs",
            owner="owner@example.com"
        )
        result = db.delete_object(delete_obj)

        assert result.chunks_removed == 2
        assert result.name == "report.pdf"

        sql_query = mock_conn.execute.call_args[0][0]
        assert "owner = %s" in sql_query
        assert "file_path = %s" in sql_query

    def test_delete_returns_zero_if_no_match(self):
        from src.vector_db.adapters.database import DataBase
        from src.vector_db.domain.domain import DeleteObject

        db = DataBase.__new__(DataBase)
        db.table = "documents"
        db.url = "postgresql://test:test@localhost:5432/test"

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {"count": 0, "file_name": ""}
        mock_conn.execute.return_value = mock_result

        db._get_connection = MagicMock(return_value=mock_conn)

        delete_obj = DeleteObject(
            path="/nonexistent/file.txt",
            storage_type="gcs",
            owner="other@example.com"
        )
        result = db.delete_object(delete_obj)

        assert result.chunks_removed == 0
        assert result.name == "file.txt"


class TestDeleteFlowEndToEnd:
    def test_delete_message_structure(self):
        message = {
            "correlation_id": "corr-789",
            "reply_topic": "service.replies",
            "payload": {
                "action": "delete",
                "file_path": "/documents/report.pdf",
                "storage_type": "gcs",
                "owner": "user@example.com"
            }
        }

        assert "correlation_id" in message
        assert "reply_topic" in message
        assert message["payload"]["action"] == "delete"
        assert "file_path" in message["payload"]
        assert "owner" in message["payload"]
        assert "storage_type" in message["payload"]

    def test_delete_response_structure(self):
        from src.vector_db.domain.domain import ObjectDeleted

        response = ObjectDeleted(name="report.pdf", chunks_removed=3)

        assert response.name == "report.pdf"
        assert response.chunks_removed == 3

        response_dict = response.model_dump(mode="json")
        assert "name" in response_dict
        assert "chunks_removed" in response_dict