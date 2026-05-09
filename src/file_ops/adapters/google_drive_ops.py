from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from typing import Optional
import io
import os
import json
import asyncio
import logging
import uuid

from aiokafka import AIOKafkaProducer
from src.file_ops.adapters.text_extractor import extract_text_from_file

logger = logging.getLogger(__name__)


class GoogleDriveOperations:
    def __init__(self, access_token: str):
        creds = Credentials(token=access_token)
        self.service = build("drive", "v3", credentials=creds)
        self._access_token = access_token
        self._bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._request_topic = os.getenv("REQUEST_TOPICS", "service.requests").split(",")[1]
        self._reply_topic = os.getenv("REPLY_TOPIC", "service.replies")


    async def _send_to_kafka(self, action: str, file_id: str, file_name: str, text: str = "", owner: Optional[str] = None):
        correlation_id = str(uuid.uuid4())
        payload = {
            "action": action,
            "file_name": file_name,
            "file_path": file_id,
            "text": text,
            "owner": owner,
            "storage_type": "drive",
        }
        command = {
            "correlation_id": correlation_id,
            "reply_topic": self._reply_topic,
            "payload": payload,
        }
        producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        try:
            await producer.start()

            # Send to event db file action
            event = {
                "owner": payload.get("owner"),
                "event": payload.get("action"),
            }
            await producer.send(self._reply_topic, event)

            # Send to vector db to do action
            await producer.send_and_wait(self._request_topic, command)
        except Exception as e:
            logger.warning(f"Failed to send {action} event to Kafka: {e}")
        finally:
            await producer.stop()


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
            await self._send_to_kafka("upload", file["id"], meta["name"], text, owner)
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
            await self._send_to_kafka("update", file["id"], file["name"], text, owner)
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

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
            await self._send_to_kafka("delete", file_path, "", "", owner)
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
            await self._send_to_kafka("rename", file["id"], new_name, "", owner)
        except Exception as e:
            logger.warning(f"Failed to send Kafka event: {e}")

        return {
            "file_id": file["id"],
            "url": file.get("webViewLink"),
            "storage_type": "drive",
        }
