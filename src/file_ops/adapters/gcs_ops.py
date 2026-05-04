from google.cloud import storage
from typing import Optional


class GCSOperations:
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        self._client = None
        self._bucket = None

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


    def upload_file(self,
                    source_path: str,
                    owner: Optional[str] = None,
                    dest_name: Optional[str] = None,
                    mime_type: Optional[str] = None,
    ) -> dict:
        blob_name = dest_name or source_path.split("/")[-1]
        blob = self.bucket.blob(blob_name)

        kwargs = {"content_type": mime_type} if mime_type else {}

        blob.upload_from_filename(source_path, **kwargs)

        # Send Command to Kafka to upload into vectordb and send Event to user

        return {
            "file_id": blob.name,
            "url": f"gs://{self.bucket_name}/{blob_name}",
            "storage_type": "gcs",
        }


    def list_files(self, directory_path: str = "/") -> list:
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


    def download_file(self, file_path: str) -> tuple[bytes, str, str]:
        blob = self.bucket.blob(file_path)
        blob.reload()
        mime_type = blob.content_type or "application/octet-stream"
        file_name = file_path.split("/")[-1]
        content = blob.download_as_bytes()
        return content, file_name, mime_type

    def delete_file(self, file_path: str) -> None:
        blob = self.bucket.blob(file_path)
        blob.delete()
