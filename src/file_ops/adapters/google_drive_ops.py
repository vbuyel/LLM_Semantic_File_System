from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from typing import Optional
import io
import os
import tempfile
import asyncio
import logging
from pathlib import Path

from src.file_ops.adapters.kafka import KafkaOperations
from src.file_ops.adapters.text_extractor import extract_text_from_file
from src.file_ops.domain.domain import SendToKafka

logger = logging.getLogger(__name__)

MIME_TO_EXT = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
}


class GoogleDriveOperations:
    def __init__(self, access_token: str):
        creds = Credentials(token=access_token)
        self.service = build("drive", "v3", credentials=creds)
        self._access_token = access_token
        self.kafka = KafkaOperations()


    async def upload_file(
        self,
        source_path: str,
        owner: Optional[str] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        folder_id: Optional[str] = None
    ) -> dict:
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

        try:
            text = extract_text_from_file(source_path)
        except Exception as e:
            logger.warning(f"Text extraction failed for {source_path}: {e}")
            text = ""

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="upload",
                    file_name=meta["name"],
                    file_path=file["id"],
                    text=text[:1000] if text else "",
                    owner=owner,
                    storage_type="drive",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": file["id"],
            "url": file.get("webViewLink"),
            "storage_type": "drive",
        }


    async def update_file(
        self,
        file_id: str,
        source_path: str,
        owner: Optional[str] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> dict:
        meta = {}
        if file_name:
            meta["name"] = file_name

        media = MediaFileUpload(
            source_path,
            mimetype=mime_type or "application/octet-stream",
            resumable=True,
        )
        
        file = self.service.files().update(
            fileId=file_id,
            body=meta,
            media_body=media,
            fields="id, name, webViewLink"
        ).execute()

        try:
            text = extract_text_from_file(source_path)
        except Exception as e:
            logger.warning(f"Text extraction failed for {source_path}: {e}")
            text = ""

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="update",
                    file_name=file["name"],
                    file_path=file["id"],
                    text=text[:1000] if text else "",
                    owner=owner,
                    storage_type="drive",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": file["id"],
            "url": file.get("webViewLink"),
            "storage_type": "drive",
        }


    async def list_files(self, owner: str, directory_path: str = "/") -> list:
        query = "'me' in owners and trashed=false"

        if directory_path != "/":
            query += f" and '{directory_path}' in parents"

        results = self.service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            q=query
        ).execute()

        await self.kafka.send_event(event="Vectorising your cloud files...", owner=owner)

        items = results.get('files', [])
        file_items = []
        for item in items:
            is_dir = item.get('mimeType') == 'application/vnd.google-apps.folder'
            size = item.get('size')

            # Download Drive file to temp location for text extraction
            text = ""
            if not is_dir:
                try:
                    content, file_name, mime_type = self.download_file(item.get('id'))
                    ext = Path(file_name).suffix if '.' in file_name else MIME_TO_EXT.get(mime_type, '')
                    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name
                    try:
                        text = extract_text_from_file(tmp_path)
                    finally:
                        os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Text extraction failed for {item.get('id')}: {e}")

            await self.kafka.send_command(
                SendToKafka(
                    action="upload",
                    file_name=item.get('name'),
                    file_path=item.get('id'),
                    text=text[:1000] if text else "",
                    owner=owner,
                    storage_type="drive",
                )
            )

            file_items.append({
                "path": item.get('id'),
                "name": item.get('name'),
                "isDirectory": is_dir,
                "size": int(size) if size else None,
                "modified": item.get('modifiedTime')
            })
        
        await self.kafka.send_event(event="Done! Files are prepared to analyze", owner=owner)
        return file_items


    def download_file(self, file_id: str) -> tuple:
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


    async def delete_file(self, file_path: str, owner: Optional[str] = None) -> None:
        self.service.files().delete(fileId=file_path).execute()
        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="delete",
                    file_name="",
                    file_path=file_path,
                    text="",
                    owner=owner,
                    storage_type="drive",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")


    async def rename_file(self, file_path: str, new_name: str, owner: Optional[str] = None) -> dict:
        print(f"[DEBUG] GoogleDrive rename: file_path={file_path}, new_name={new_name}")
        file = self.service.files().update(
            fileId=file_path,
            body={"name": new_name},
            fields="id, name, webViewLink"
        ).execute()

        try:
            await self.kafka.send_command(
                SendToKafka(
                    action="rename",
                    file_name=new_name,
                    file_path=file["id"],
                    text="",
                    owner=owner,
                    storage_type="drive",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": file["id"],
            "url": file.get("webViewLink"),
            "storage_type": "drive",
        }
