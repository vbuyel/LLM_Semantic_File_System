from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from typing import Optional
import io
import asyncio
import logging
import time
from pathlib import Path

from src.file_ops.adapters.kafka import KafkaOperations
from src.file_ops.adapters.text_extractor import (
    clean_text,
    extract_text_from_bytes,
    extract_text_from_file,
    is_readable,
)
from src.file_ops.domain.domain import SendToKafka

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 150 * 1024  # 150KB per Kafka message — keeps each msg safely under broker limits

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


    @staticmethod
    def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
        """Split text at word boundaries, keeping each chunk ≤ max_chars."""
        if len(text) <= max_chars:
            return [text]
        words = text.split()
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for word in words:
            word_len = len(word)
            sep = 1 if current else 0
            if current_len + sep + word_len > max_chars and current:
                chunks.append(" ".join(current))
                current = [word]
                current_len = word_len
            else:
                current_len += sep + word_len
                current.append(word)
        if current:
            chunks.append(" ".join(current))
        return chunks

    async def _send_chunked_kafka(
        self, action: str, file_name: str, file_path: str, text: str,
        owner: Optional[str], storage_type: str,
    ) -> None:
        text = clean_text(text)
        if not is_readable(text):
            logger.info(f"Skipping {file_path}: no readable text after cleaning")
            return

        raw_chunks = self._chunk_text(text)
        chunks = [c for c in raw_chunks if is_readable(c)]
        if not chunks:
            logger.info(f"Skipping {file_path}: no readable chunks after filtering")
            return

        for i, chunk in enumerate(chunks):
            try:
                await self.kafka.send_command(
                    SendToKafka(
                        action=action,
                        file_name=file_name,
                        file_path=file_path,
                        text=chunk,
                        owner=owner,
                        storage_type=storage_type,
                        chunk_index=i,
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send Kafka event (chunk {i+1}/{len(chunks)}): {e}"
                )

    def _download_file_with_retry(
        self, file_id: str, mime_type: Optional[str] = None,
        file_name: Optional[str] = None, max_retries: int = 3,
    ) -> tuple:
        for attempt in range(max_retries):
            try:
                return self.download_file(file_id, mime_type, file_name)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        f"Download failed for {file_id} "
                        f"(attempt {attempt+1}/{max_retries}): {e}. "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    raise

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

        await self._send_chunked_kafka(
            "upload", meta["name"], file["id"], text, owner, "drive",
        )

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

        await self._send_chunked_kafka(
            "upload", file["name"], file["id"], text, owner, "drive",
        )

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
        # httplib2 (googleapiclient) is NOT thread-safe — segfaults with concurrent
        # downloads. Serialise all Drive API calls through one thread at a time.
        sem = asyncio.Semaphore(1)

        async def process_item(item):
            async with sem:
                is_dir = item.get('mimeType') == 'application/vnd.google-apps.folder'
                text = ""

                if not is_dir:
                    try:
                        content, file_name, mime_type = await asyncio.to_thread(
                            self._download_file_with_retry,
                            item['id'], item.get('mimeType'), item.get('name'),
                        )
                        ext = Path(file_name).suffix if '.' in file_name else MIME_TO_EXT.get(mime_type, '')
                        if content:
                            text = extract_text_from_bytes(content, ext)
                    except Exception as e:
                        logger.warning(f"Text extraction failed for {item.get('id')}: {e}")

                await self._send_chunked_kafka(
                    "upload", item.get('name'), item.get('id'), text, owner, "drive",
                )

                return {
                    "path": item.get('id'),
                    "name": item.get('name'),
                    "isDirectory": is_dir,
                    "size": int(item.get('size')) if item.get('size') else None,
                    "modified": item.get('modifiedTime'),
                }

        results_list = await asyncio.gather(*[process_item(item) for item in items])
        file_items = [r for r in results_list if r is not None]

        await self.kafka.send_event(event="Done! Files are prepared to analyze", owner=owner)
        return file_items


    def download_file(self, file_id: str, mime_type: Optional[str] = None, file_name: Optional[str] = None) -> tuple:
        EXPORT_FORMATS = {
            "application/vnd.google-apps.document":
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.google-apps.spreadsheet":
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation":
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }

        if mime_type is None or file_name is None:
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
