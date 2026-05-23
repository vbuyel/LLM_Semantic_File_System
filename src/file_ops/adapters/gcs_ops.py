import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from google.cloud import storage
from typing import Optional
import os

from adapters.kafka import KafkaOperations
from adapters.text_extractor import TextExtractorOperations
from domain.domain import SendToKafka

logger = logging.getLogger(__name__)


class GCSOperations:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._client = None
        self._bucket = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.kafka = KafkaOperations()
        self.text_extractor = TextExtractorOperations()
        self.owner_ops = "guest"


    @property
    def client(self) -> storage.Client:
        """Get the GCS client"""
        if self._client is None:
            self._client = storage.Client()
        return self._client


    @property
    def bucket(self) -> storage.Bucket:
        """Get the GCS bucket"""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket


    async def upload_file(
        self,
        owner: str,
        source_path: str,
        dest_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> dict:
        """Upload a file to GCS"""
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
            text = self.text_extractor.extract_text_from_file(source_path)
        except Exception as e:
            logger.warning(f"Text extraction failed for {source_path}: {e}")
            text = ""

        file_path = "root/"
        try:
            await self.text_extractor.send_chunked_kafka(
                action="upload",
                file_name=blob_name,
                file_path=file_path,
                text=text,
                owner=owner,
                storage_type="gcs",
                file_size=os.path.getsize(source_path),
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": blob_name,
            "url": f"gs://{self.bucket_name}/{blob_name}",
            "storage_type": "gcs",
        }


    def list_files(self, directory_path: str = "/") -> list:
        """List files in a directory"""
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
        """Download a file from GCS"""
        if not file_path:
            raise ValueError("file_path cannot be empty")

        blob = self.bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in bucket: {file_path}")

        mime_type = blob.content_type or "application/octet-stream"
        file_name = file_path.split("/")[-1]
        content = blob.download_as_bytes()
        return (content, file_name, mime_type)


    async def delete_file(self, file_path: str, owner: str) -> None:
        """Delete a file from GCS"""
        if not file_path:
            raise ValueError("file_path cannot be empty")

        blob = self.bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in bucket: {file_path}")

        blob.delete()

        db_file_path = "root/"
        db_file_name = file_path.split("/")[-1]
        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="delete",
                    file_name=db_file_name,
                    file_path=db_file_path,
                    text="",
                    owner=owner,
                    storage_type="gcs",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")


    async def rename_file(self, file_path: str, new_name: str, owner: str) -> dict:
        """Rename a file in GCS"""
        if not file_path:
            raise ValueError("file_path cannot be empty")
        if not new_name:
            raise ValueError("new_name cannot be empty")

        blob = self.bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in bucket: {file_path}")

        old_file_name = file_path.split("/")[-1]
        new_blob_name = new_name
        self.bucket.rename_blob(blob, new_blob_name)

        old_db_path = "root/"
        new_db_path = "root/"

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="rename",
                    file_name=new_name,
                    file_path=old_db_path,
                    new_path=new_db_path,
                    old_file_name=old_file_name,
                    text="",
                    owner=owner,
                    storage_type="gcs",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": new_name,
            "url": f"gs://{self.bucket_name}/{new_blob_name}",
            "storage_type": "gcs",
        }
