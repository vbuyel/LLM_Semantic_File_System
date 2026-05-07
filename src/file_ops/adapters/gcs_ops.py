import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from aiokafka import AIOKafkaProducer
from google.cloud import storage
from typing import Optional
import os

from src.file_ops.adapters.text_extractor import extract_text_from_file

logger = logging.getLogger(__name__)


class GCSOperations:
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        self._client = None
        self._bucket = None
        self._executor = ThreadPoolExecutor(max_workers=2)

        self._bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._request_topic = os.getenv("REQUEST_TOPICS", "service.requests").split(",")[0]
        self._reply_topic = os.getenv("REPLY_TOPIC", "service.replies")


    @property
    def client(self):
        if self._client is None:
            if self.credentials_path:
                self._client = storage.Client.from_service_account_json(self.credentials_path)
            else:
                self._client = storage.Client()
        return self._client


    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket


    async def _send_kafka_event(self, payload: dict):
        correlation_id = str(uuid.uuid4())
        event = {
            "correlation_id": correlation_id,
            "reply_topic": self._reply_topic,
            "payload": payload,
        }
        print(f"[DEBUG] Sending to Kafka topic: {self._request_topic}")
        producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        try:
            await producer.start()
            await producer.send_and_wait(self._request_topic, event)
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")
        finally:
            await producer.stop()


    async def upload_file(
        self,
        source_path: str,
        owner: Optional[str] = None,
        dest_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> dict:
        if not source_path:
            raise ValueError("source_path cannot be empty")
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        blob_name = dest_name or source_path.split("/")[-1]
        blob = self.bucket.blob(blob_name)

        kwargs = {"content_type": mime_type} if mime_type else {}

        await asyncio.get_event_loop().run_in_executor(
            self._executor, lambda: blob.upload_from_filename(source_path, **kwargs)
        )

        try:
            text = extract_text_from_file(source_path)
        except Exception as e:
            logger.warning(f"Text extraction failed for {source_path}: {e}")
            text = ""

        message = {
            "action": "upload",
            "file_name": blob_name,
            "file_path": f"gs://{self.bucket_name}/{blob_name}",
            "text": text[:1000] if text else "",
            "owner": owner,
            "storage_type": "gcs",
        }

        await self._send_kafka_event(message)

        return {
            "file_id": blob_name,
            "url": f"gs://{self.bucket_name}/{blob_name}",
            "storage_type": "gcs",
        }


    def list_files(self, directory_path: str = "/") -> list:
        if directory_path is None:
            directory_path = "/"
        prefix = directory_path.lstrip("/")
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        files = []

        blobs = self.client.list_blobs(self.bucket, prefix=prefix, delimiter="/")

        for prefix_name in blobs.prefixes:
            folder_name = prefix_name.rstrip("/").split("/")[-1]
            files.append({
                "path": prefix_name,
                "name": folder_name,
                "isDirectory": True,
                "size": None,
                "modified": None,
            })

        for blob in blobs:
            files.append({
                "path": blob.name,
                "name": blob.name.split("/")[-1],
                "isDirectory": False,
                "size": blob.size,
                "modified": blob.updated.isoformat() if blob.updated else None,
            })

        return files


    def download_file(self, file_path: str) -> tuple:
        if not file_path:
            raise ValueError("file_path cannot be empty")

        blob = self.bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in bucket: {file_path}")

        mime_type = blob.content_type or "application/octet-stream"
        file_name = file_path.split("/")[-1]
        content = blob.download_as_bytes()
        return (content, file_name, mime_type)

    def delete_file(self, file_path: str) -> None:
        if not file_path:
            raise ValueError("file_path cannot be empty")

        blob = self.bucket.blob(file_path)
        if blob.exists():
            blob.delete()
        else:
            raise FileNotFoundError(f"File not found in bucket: {file_path}")
