import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from google.cloud import storage
from typing import Optional
import os

from src.file_ops.adapters.kafka import KafkaOperations
from src.file_ops.adapters.text_extractor import extract_text_from_file
from src.file_ops.domain.domain import SendToKafka

logger = logging.getLogger(__name__)


class GCSOperations:
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        self._client = None
        self._bucket = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.kafka = KafkaOperations()


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


    async def upload_file(
        self,
        source_path: str,
        owner: Optional[str] = None,
        dest_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> dict:
        return await self._process_file_action("upload", source_path, owner, dest_name, mime_type)


    async def update_file(
        self,
        source_path: str,
        owner: Optional[str] = None,
        dest_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> dict:
        return await self._process_file_action("update", source_path, owner, dest_name, mime_type)


    async def _process_file_action(
        self,
        action: str,
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

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action=action,
                    file_name=blob_name,
                    file_path=f"gs://{self.bucket_name}/{blob_name}",
                    text=text[:1000] if text else "",
                    owner=owner,
                    storage_type="gcs",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

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


    async def delete_file(self, file_path: str, owner: Optional[str] = None) -> None:
        if not file_path:
            raise ValueError("file_path cannot be empty")

        blob = self.bucket.blob(file_path)
        file_existed = blob.exists()
        if file_existed:
            blob.delete()

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="delete",
                    file_name=file_path,
                    file_path=f"gs://{self.bucket_name}/{file_path}",
                    text="",
                    owner=owner,
                    storage_type="gcs",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        if not file_existed:
            raise FileNotFoundError(f"File not found in bucket: {file_path}")


    async def rename_file(self, file_path: str, new_name: str, owner: Optional[str] = None) -> dict:
        if not file_path:
            raise ValueError("file_path cannot be empty")
        if not new_name:
            raise ValueError("new_name cannot be empty")

        blob = self.bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in bucket: {file_path}")

        self.bucket.rename_blob(blob, new_name)

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="rename",
                    file_name=new_name,
                    file_path=f"gs://{self.bucket_name}/{file_path}",
                    text="",
                    owner=owner,
                    storage_type="gcs",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": new_name,
            "url": f"gs://{self.bucket_name}/{new_name}",
            "storage_type": "gcs",
        }
