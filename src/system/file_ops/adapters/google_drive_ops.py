"""
Google Drive Operations

Setup Instructions:
1. Create a project at https://console.cloud.google.com/
2. Enable the Google Drive API
3. Create OAuth credentials (Desktop app or Web application)
4. Download the credentials.json file
5. Set up refresh token using the OAuth flow
6. Set environment variables:
   - GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json
   - GOOGLE_DRIVE_REFRESH_TOKEN=your_refresh_token
   - Or use Service Account for server-side operations
"""


import os
from typing import List, Dict, Any
from pathlib import Path
import io

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
    from googleapiclient.errors import HttpError

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleDriveOperations:
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        if not GOOGLE_AVAILABLE:
            print(
                "Google API libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
            return

        creds = None
        token_path = Path.home() / ".config" / "llm-sfs" / "gdrive_token.json"

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        if not creds or not creds.valid:
            credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH")

            if credentials_path and Path(credentials_path).exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            else:
                print(
                    "Google Drive not authenticated. Set GOOGLE_DRIVE_CREDENTIALS_PATH environment variable."
                )
                return

        self.service = build("drive", "v3", credentials=creds)

    def _file_to_dict(self, file: Dict) -> Dict[str, Any]:
        return {
            "name": file.get("name", "Unknown"),
            "id": file.get("id"),
            "mimeType": file.get("mimeType"),
            "isDirectory": file.get("mimeType") == "application/vnd.google-apps.folder",
            "size": int(file.get("size", 0)),
            "modified": file.get("modifiedTime", ""),
            "parents": file.get("parents", []),
            "webViewLink": file.get("webViewLink"),
        }

    def list_files(self, folder_id: str = "root") -> List[Dict[str, Any]]:
        if not self.service:
            return []

        results = []
        page_token = None

        while True:
            try:
                query = f"'{folder_id}' in parents and trashed=false"
                response = (
                    self.service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                        pageToken=page_token,
                    )
                    .execute()
                )

                for file in response.get("files", []):
                    results.append(self._file_to_dict(file))

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            except HttpError as error:
                print(f"Google Drive API error: {error}")
                break

        return results

    def upload_file(self, file, folder_id: str = "root") -> Dict[str, Any]:
        if not self.service:
            return {"status": "error", "message": "Not authenticated"}

        try:
            file_metadata = {"name": file.filename, "parents": [folder_id]}

            if hasattr(file, "file"):
                media = MediaIoBaseUpload(
                    file.file, mimetype=file.content_type or "application/octet-stream"
                )
            else:
                media = MediaFileUpload(
                    file, mimetype=file.content_type or "application/octet-stream"
                )

            uploaded_file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, mimeType, size, modifiedTime",
                )
                .execute()
            )

            return {"status": "success", "file": self._file_to_dict(uploaded_file)}

        except HttpError as error:
            return {"status": "error", "message": str(error)}

    def create_folder(self, name: str, parent_id: str = "root") -> Dict[str, Any]:
        if not self.service:
            return {"status": "error", "message": "Not authenticated"}

        try:
            file_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }

            folder = (
                self.service.files()
                .create(body=file_metadata, fields="id, name")
                .execute()
            )

            return {"status": "success", "folder": self._file_to_dict(folder)}

        except HttpError as error:
            return {"status": "error", "message": str(error)}

    def move_file(self, file_id: str, target_folder_id: str) -> Dict[str, Any]:
        if not self.service:
            return {"status": "error", "message": "Not authenticated"}

        try:
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", []))

            updated_file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    addParents=target_folder_id,
                    removeParents=previous_parents,
                    fields="id, name, parents",
                )
                .execute()
            )

            return {"status": "success", "file": self._file_to_dict(updated_file)}

        except HttpError as error:
            return {"status": "error", "message": str(error)}

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        if not self.service:
            return {"status": "error", "message": "Not authenticated"}

        try:
            self.service.files().delete(fileId=file_id).execute()
            return {"status": "success", "deleted": file_id}

        except HttpError as error:
            return {"status": "error", "message": str(error)}

    def download_file(self, file_id: str, destination: Path) -> Dict[str, Any]:
        if not self.service:
            return {"status": "error", "message": "Not authenticated"}

        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(destination, "wb") as f:
                downloader = io.FileIO(f.fileno(), mode="wb")
                media = MediaIoBaseUpload(downloader, chunksize=1024 * 1024)

                while True:
                    chunk = request.execute(num_retries=5)
                    if not chunk:
                        break
                    downloader.write(chunk)

            return {"status": "success", "path": str(destination)}

        except HttpError as error:
            return {"status": "error", "message": str(error)}


# Setup Guide for Google Drive Authentication:
# =============================================
#
# Option 1: OAuth 2.0 for Desktop/Mobile Apps
# -------------------------------------------
# 1. Go to https://console.cloud.google.com/apis/credentials
# 2. Create OAuth Client ID (Desktop app type)
# 3. Download the JSON file
# 4. Set GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json
# 5. On first run, browser will open for authentication
# 6. Token will be saved for future use
#
# Option 2: Service Account (Recommended for Server)
# --------------------------------------------------
# 1. Create a Service Account in Google Cloud Console
# 2. Download the JSON key file
# 3. Share your Google Drive folders with the service account email
# 4. Set GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/key.json
#
# Environment Variables:
# - GOOGLE_DRIVE_CREDENTIALS_PATH: Path to OAuth credentials.json
# - GOOGLE_SERVICE_ACCOUNT_KEY: Path to service account key.json
