from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from typing import Optional
import io


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
        query = "'me' in owners and trashed=false"
        
        if directory_path != "/":
            query += f" and '{directory_path}' in parents"
        
        results = self.service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            q=query
        ).execute()
        
        items = results.get('files', [])
        file_items = []
        for item in items:
            is_dir = item.get('mimeType') == 'application/vnd.google-apps.folder'
            size = item.get('size')
            file_items.append({
                "path": item.get('id'),
                "name": item.get('name'),
                "isDirectory": is_dir,
                "size": int(size) if size else None,
                "modified": item.get('modifiedTime')
            })
        return file_items

    def download_file(self, file_id: str) -> tuple[bytes, str, str]:
        """Download a file from Google Drive.

        Handles both regular binary files (via get_media) and Google Workspace
        files such as Docs, Sheets, and Slides (via export_media).

        Returns:
            (file_bytes, filename, mime_type)
        """
        # Google Workspace MIME types → preferred export formats
        EXPORT_FORMATS = {
            "application/vnd.google-apps.document":
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.google-apps.spreadsheet":
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation":
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }

        meta = self.service.files().get(
            fileId=file_id, fields="name,mimeType"
        ).execute()
        mime_type = meta.get("mimeType", "application/octet-stream")
        file_name = meta.get("name", file_id)

        buffer = io.BytesIO()
        if mime_type in EXPORT_FORMATS:
            export_mime = EXPORT_FORMATS[mime_type]
            request = self.service.files().export_media(
                fileId=file_id, mimeType=export_mime
            )
            mime_type = export_mime
        else:
            request = self.service.files().get_media(fileId=file_id)

        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue(), file_name, mime_type

    def delete_file(self, file_path: str) -> None:
        raise NotImplementedError("Google Drive delete_file not yet implemented")
