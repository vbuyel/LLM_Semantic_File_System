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
                    dest_name: Optional[str] = None,
                    mime_type: Optional[str] = None) -> dict:
        blob_name = dest_name or source_path.split("/")[-1]
        blob = self.bucket.blob(blob_name)

        kwargs = {"content_type": mime_type} if mime_type else {}

        blob.upload_from_filename(source_path, **kwargs)
        blob.make_public()

        return {
            "file_id": blob.name,
            "url": blob.public_url,
            "storage_type": "gcs",
        }

    def list_files(self, directory_path: str = "/") -> list:
        raise NotImplementedError("GCS list_files not yet implemented")

    def delete_file(self, file_path: str) -> None:
        raise NotImplementedError("GCS delete_file not yet implemented")
