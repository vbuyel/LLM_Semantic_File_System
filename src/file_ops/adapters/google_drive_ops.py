from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from typing import Optional


class GoogleDriveOperations:
    def __init__(self, access_token: str):
        creds = Credentials(token=access_token)
        self.service = build("drive", "v3", credentials=creds)


    def upload_file(self, source_path: str, file_name: Optional[str] = None,
                   mime_type: Optional[str] = None,
                   folder_id: Optional[str] = None) -> dict:
        meta = {"name": file_name or source_path.split("/")[-1]}

        if folder_id:
            meta["parents"] = [folder_id]
        
        media = MediaFileUpload(
            source_path,
            mimetype=mime_type or "application/octet-stream",
            resumable=True,
        )
        file = self.service.files().create(
            body=meta, media_body=media, fields="id,webViewLink"
        ).execute()

        return {
            "file_id": file["id"],
            "url": file.get("webViewLink"),
            "storage_type": "drive",
        }

    def list_files(self, directory_path: str = "/") -> list:
        raise NotImplementedError("Google Drive list_files not yet implemented")

    def delete_file(self, file_path: str) -> None:
        raise NotImplementedError("Google Drive delete_file not yet implemented")
