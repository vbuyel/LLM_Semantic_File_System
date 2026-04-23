from google.cloud import storage
from typing import Optional


class GCSOperations:
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        if credentials_path:
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)


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
