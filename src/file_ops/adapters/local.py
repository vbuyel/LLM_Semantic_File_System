from pathlib import Path
import os
import shutil
import datetime
from typing import Optional, List, Dict


class LocalOperations:
    def __init__(self, base_path: Optional[str] = None):
        if base_path is not None:
            self.base_path = Path(base_path)
        else:
            env_path = os.getenv("LOCAL_STORAGE_PATH")
            if env_path is not None:
                self.base_path = Path(env_path)
            else:
                self.base_path = Path("./local_storage")

        self.base_path = self.base_path.resolve()

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Permission denied to create base directory {self.base_path}")
        except Exception as e:
            raise ValueError(f"Failed to create base directory {self.base_path}: {str(e)}")

    def list_files(self, directory_path: str = "/") -> List[Dict]:
        normalized_dir = directory_path.lstrip("/")
        target_dir = self.base_path / normalized_dir

        if not target_dir.exists():
            raise ValueError(f"Directory '{directory_path}' not found in local storage")
        if not target_dir.is_dir():
            raise ValueError(f"'{directory_path}' is not a directory")

        entries = []
        try:
            for entry in target_dir.iterdir():
                rel_path = entry.relative_to(self.base_path).as_posix()
                name = entry.name
                is_dir = entry.is_dir()

                size = None
                modified = None

                if entry.is_file():
                    try:
                        size = os.path.getsize(entry)
                        mtime = os.path.getmtime(entry)
                        modified = datetime.datetime.fromtimestamp(mtime).isoformat()
                    except OSError as e:
                        raise ValueError(f"Failed to get stats for {rel_path}: {str(e)}")

                entries.append({
                    "path": rel_path,
                    "name": name,
                    "isDirectory": is_dir,
                    "size": size,
                    "modified": modified
                })
        except PermissionError:
            raise ValueError(f"Permission denied to list directory '{directory_path}'")

        entries.sort(key=lambda x: (0 if x["isDirectory"] else 1, x["name"].lower()))
        return entries

    def upload_file(self, source_path: str, dest_name: str, mime_type: str = None) -> Dict:
        source = Path(source_path)
        if not source.exists():
            raise ValueError(f"Source file '{source_path}' not found")
        if not source.is_file():
            raise ValueError(f"'{source_path}' is not a file")

        dest_path = self.base_path / dest_name
        dest_resolved = dest_path.resolve()
        base_resolved = self.base_path.resolve()

        if not str(dest_resolved).startswith(str(base_resolved)):
            raise ValueError(f"Destination path '{dest_name}' is outside base storage directory")

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Permission denied to create directory for '{dest_name}'")

        try:
            shutil.copy2(source_path, dest_path)
        except FileNotFoundError:
            raise ValueError(f"Source file '{source_path}' not found")
        except PermissionError:
            raise ValueError(f"Permission denied when writing to '{dest_name}'")
        except Exception as e:
            raise ValueError(f"Failed to upload file: {str(e)}")

        return {
            "file_id": Path(dest_name).as_posix(),
            "url": None,
            "storage_type": "local"
        }

    def delete_file(self, file_path: str) -> None:
        target_path = self.base_path / file_path
        target_resolved = target_path.resolve()
        base_resolved = self.base_path.resolve()

        if not str(target_resolved).startswith(str(base_resolved)):
            raise ValueError(f"File path '{file_path}' is outside base storage directory")

        if not target_path.exists():
            raise ValueError(f"File or directory '{file_path}' not found in local storage")

        try:
            if target_path.is_dir():
                shutil.rmtree(target_path)
            elif target_path.is_file():
                os.remove(target_path)
            else:
                raise ValueError(f"'{file_path}' is not a valid file or directory")
        except PermissionError:
            raise ValueError(f"Permission denied to delete '{file_path}'")
        except Exception as e:
            raise ValueError(f"Failed to delete '{file_path}': {str(e)}")
