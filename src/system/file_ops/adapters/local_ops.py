"""Local file system operations"""


from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import shutil


class LocalFileOperations:
    def __init__(self, storage_root: Path):
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        dir_path = Path(path)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            return []

        files = []
        for item in sorted(
            dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
        ):
            stat = item.stat()
            files.append(
                {
                    "name": item.name,
                    "path": str(item.relative_to(self.storage_root)),
                    "size": stat.st_size if item.is_file() else 0,
                    "isDirectory": item.is_dir(),
                    "type": self._get_file_type(item),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )
        return files

    def _get_file_type(self, path: Path) -> str:
        if path.is_dir():
            return "Folder"

        ext = path.suffix.lower()
        types = {
            ".pdf": "PDF Document",
            ".doc": "Word Document",
            ".docx": "Word Document",
            ".txt": "Text File",
            ".md": "Markdown",
            ".jpg": "JPEG Image",
            ".jpeg": "JPEG Image",
            ".png": "PNG Image",
            ".gif": "GIF Image",
            ".mp3": "MP3 Audio",
            ".mp4": "MP4 Video",
            ".zip": "ZIP Archive",
            ".py": "Python File",
            ".js": "JavaScript",
            ".html": "HTML File",
            ".css": "CSS File",
        }
        return types.get(ext, "File")

    async def upload_file(self, path: str, file) -> Dict[str, Any]:
        file_path = Path(path) / file.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        content = await file.read()
        file_path.write_bytes(content)

        return {
            "status": "success",
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path.relative_to(self.storage_root)),
        }

    def move_file(self, source_path: str, target_path: str) -> Dict[str, Any]:
        source = self.storage_root / source_path.lstrip("/")
        target = self.storage_root / target_path.lstrip("/")

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))

        return {
            "status": "success",
            "source": str(source.relative_to(self.storage_root)),
            "target": str(target.relative_to(self.storage_root)),
        }

    def rename_file(self, path: str, new_name: str) -> Dict[str, Any]:
        file_path = self.storage_root / path.lstrip("/")
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        new_path = file_path.parent / new_name
        file_path.rename(new_path)

        return {
            "status": "success",
            "oldPath": str(file_path.relative_to(self.storage_root)),
            "newPath": str(new_path.relative_to(self.storage_root)),
        }

    def delete_file(self, path: str) -> Dict[str, Any]:
        file_path = self.storage_root / path.lstrip("/")
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()

        return {
            "status": "success",
            "deleted": str(file_path.relative_to(self.storage_root)),
        }
