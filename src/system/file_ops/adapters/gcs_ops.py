"""
Google Cloud Storage Operations

Setup Instructions:
1. Create a project at https://console.cloud.google.com/
2. Enable the Cloud Storage API
3. Create a Service Account with Storage Admin role
4. Download the JSON key file
5. Set environment variable:
   - GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   - GCS_BUCKET_NAME=your-default-bucket-name
"""


import os
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

try:
    from google.cloud import storage
    from google.cloud.storage import Blob
    from google.api_core.exceptions import NotFound, GoogleAPIError

    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False


class GCSOperations:
    def __init__(self):
        self.client = None
        self.default_bucket = os.getenv("GCS_BUCKET_NAME")
        self._authenticate()

    def _authenticate(self):
        if not GCS_AVAILABLE:
            print(
                "Google Cloud Storage library not installed. Run: pip install google-cloud-storage"
            )
            return

        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if credentials_path and Path(credentials_path).exists():
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            try:
                self.client = storage.Client()
            except Exception as e:
                print(
                    f"GCS authentication failed: {e}. Set GOOGLE_APPLICATION_CREDENTIALS environment variable."
                )

    def _blob_to_dict(self, blob: Blob) -> Dict[str, Any]:
        return {
            "name": blob.name.split("/")[-1] if "/" in blob.name else blob.name,
            "path": blob.name,
            "bucket": blob.bucket.name,
            "size": blob.size or 0,
            "isDirectory": blob.name.endswith("/"),
            "modified": blob.updated.strftime("%Y-%m-%d %H:%M")
            if blob.updated
            else None,
            "url": blob.public_url if blob.public_url else None,
            "generation": blob.generation,
        }

    def list_files(
        self, bucket_name: str = None, prefix: str = ""
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        bucket_name = bucket_name or self.default_bucket
        if not bucket_name:
            return []

        try:
            bucket = self.client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

            results = []
            for blob in blobs:
                if not blob.name.endswith("/"):
                    results.append(self._blob_to_dict(blob))

            for prefix in blobs.prefixes:
                results.append(
                    {
                        "name": prefix.rstrip("/").split("/")[-1],
                        "path": prefix.rstrip("/"),
                        "bucket": bucket_name,
                        "size": 0,
                        "isDirectory": True,
                        "modified": None,
                    }
                )

            return results

        except NotFound:
            print(f"Bucket '{bucket_name}' not found")
            return []
        except GoogleAPIError as e:
            print(f"GCS error: {e}")
            return []

    async def upload_file(
        self, file, bucket_name: str = None, destination: str = None
    ) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        bucket_name = bucket_name or self.default_bucket
        if not bucket_name:
            return {"status": "error", "message": "No bucket specified"}

        try:
            bucket = self.client.bucket(bucket_name)
            dest_path = destination or file.filename

            blob = bucket.blob(dest_path)

            if hasattr(file, "file"):
                content = await file.read()
                blob.upload_from_string(
                    content,
                    content_type=file.content_type or "application/octet-stream",
                )
            else:
                blob.upload_from_filename(
                    file, content_type=file.content_type or "application/octet-stream"
                )

            return {"status": "success", "file": self._blob_to_dict(blob)}

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def upload_from_string(
        self,
        bucket_name: str,
        destination: str,
        content: str,
        content_type: str = "text/plain",
    ) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination)
            blob.upload_from_string(content, content_type=content_type)

            return {"status": "success", "file": self._blob_to_dict(blob)}

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def download_file(
        self, bucket_name: str, source_path: str, destination: Path
    ) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(source_path)
            blob.download_to_filename(str(destination))

            return {"status": "success", "path": str(destination)}

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def move_file(
        self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str
    ) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            source_blob = self.client.bucket(source_bucket).blob(source_path)

            if source_bucket == dest_bucket:
                new_blob = self.client.bucket(dest_bucket).blob(dest_path)
                new_blob.rewrite(source_blob)
                source_blob.delete()
            else:
                source_bucket_obj = self.client.bucket(source_bucket)
                source_blob = source_bucket_obj.blob(source_path)

                dest_bucket_obj = self.client.bucket(dest_bucket)
                new_blob = dest_bucket_obj.blob(dest_path)

                new_blob.rewrite(source_blob)
                source_blob.delete()

            return {
                "status": "success",
                "source": f"gs://{source_bucket}/{source_path}",
                "target": f"gs://{dest_bucket}/{dest_path}",
            }

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def rename_file(
        self, bucket_name: str, source_path: str, new_name: str
    ) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        directory = "/".join(source_path.split("/")[:-1])
        dest_path = f"{directory}/{new_name}" if directory else new_name

        return self.move_file(bucket_name, source_path, bucket_name, dest_path)

    def delete_file(self, bucket_name: str, file_path: str) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            blob.delete()

            return {"status": "success", "deleted": f"gs://{bucket_name}/{file_path}"}

        except NotFound:
            return {
                "status": "error",
                "message": f"File not found: gs://{bucket_name}/{file_path}",
            }
        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def create_folder(self, bucket_name: str, folder_path: str) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(folder_path + "/")
            blob.upload_from_string("")

            return {"status": "success", "folder": f"gs://{bucket_name}/{folder_path}/"}

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def get_signed_url(
        self, bucket_name: str, file_path: str, expiration: int = 3600
    ) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            url = blob.generate_signed_url(
                expiration=datetime.timedelta(seconds=expiration)
            )

            return {"status": "success", "url": url}

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}

    def make_public(self, bucket_name: str, file_path: str) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Not authenticated"}

        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            blob.make_public()

            return {"status": "success", "url": blob.public_url}

        except GoogleAPIError as e:
            return {"status": "error", "message": str(e)}


# Setup Guide for Google Cloud Storage:
# ======================================
#
# 1. Create Google Cloud Project
#    - Go to https://console.cloud.google.com/
#    - Create new project or select existing
#
# 2. Enable Cloud Storage API
#    - Go to APIs & Services > Library
#    - Search for "Cloud Storage"
#    - Enable the API
#
# 3. Create Service Account (Recommended)
#    - Go to APIs & Services > Credentials
#    - Click "Create Credentials" > "Service Account"
#    - Name it (e.g., "llm-sfs-gcs")
#    - Grant roles: "Storage Admin" or "Storage Object Admin"
#    - Create and download JSON key file
#
# 4. Set Environment Variables:
#    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
#    export GCS_BUCKET_NAME="your-bucket-name"
#
# 5. For local development, you can use:
#    - gsutil to create test buckets
#    - Google Cloud Storage Emulator (https://cloud.google.com/storage/docs/emulator)
#
# 6. CORS Configuration (for browser uploads):
#    gsutil cors set cors.json gs://your-bucket-name
#
#    cors.json:
#    [
#        {
#            "origin": ["http://localhost:8000"],
#            "method": ["GET", "POST", "PUT", "DELETE", "HEAD"],
#            "responseHeader": ["Content-Type", "Authorization"],
#            "maxAgeSeconds": 3600
#        }
#    ]
