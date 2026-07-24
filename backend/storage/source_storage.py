"""Private cloud storage for indexed project source files."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from backend.storage.supabase_client import get_supabase_client
from config.settings import settings


@dataclass(frozen=True)
class StoredSourceFile:
    path: str
    size_bytes: int


class SupabaseSourceStorage:
    """Store project files in a private Supabase Storage bucket."""

    def __init__(self, client=None, bucket: str | None = None):
        self._client = client or get_supabase_client()
        self.bucket = bucket or settings.supabase_source_bucket

    def upload_files(
        self,
        repository_id: str,
        root: Path,
        files: Iterable[Path],
    ) -> int:
        bucket = self._client.storage.from_(self.bucket)
        uploaded = 0
        for file_path in files:
            resolved = file_path.resolve()
            relative = resolved.relative_to(root.resolve()).as_posix()
            object_path = f"{repository_id}/{relative}"
            bucket.upload(
                object_path,
                resolved.read_bytes(),
                {"upsert": "true"},
            )
            uploaded += 1
        return uploaded

    def list_files(self, repository_id: str) -> List[StoredSourceFile]:
        bucket = self._client.storage.from_(self.bucket)
        found: List[StoredSourceFile] = []

        def walk(prefix: str) -> None:
            for item in bucket.list(prefix):
                name = item["name"]
                object_path = f"{prefix}/{name}" if prefix else name
                metadata = item.get("metadata")
                if metadata is None:
                    walk(object_path)
                    continue
                relative = object_path.removeprefix(f"{repository_id}/")
                found.append(
                    StoredSourceFile(
                        path=relative,
                        size_bytes=int(metadata.get("size", 0)),
                    )
                )

        walk(repository_id)
        return sorted(found, key=lambda item: item.path)

    def read_file(self, repository_id: str, path: str) -> bytes:
        safe_path = self._safe_relative_path(path)
        return self._client.storage.from_(self.bucket).download(
            f"{repository_id}/{safe_path}"
        )

    def delete_repository(self, repository_id: str) -> int:
        """Delete every stored source object for one repository."""
        safe_repository_id = self._safe_repository_id(repository_id)
        bucket = self._client.storage.from_(self.bucket)
        object_paths: List[str] = []

        def walk(prefix: str) -> None:
            for item in bucket.list(prefix):
                name = item["name"]
                object_path = f"{prefix}/{name}" if prefix else name
                if item.get("metadata") is None:
                    walk(object_path)
                else:
                    object_paths.append(object_path)

        walk(safe_repository_id)
        for start in range(0, len(object_paths), 100):
            bucket.remove(object_paths[start:start + 100])
        return len(object_paths)

    @staticmethod
    def _safe_repository_id(repository_id: str) -> str:
        normalized = repository_id.strip()
        if (
            not normalized
            or "/" in normalized
            or "\\" in normalized
            or normalized in {".", ".."}
        ):
            raise ValueError("Unsafe repository ID")
        return normalized

    @staticmethod
    def _safe_relative_path(path: str) -> str:
        normalized = path.replace("\\", "/").strip("/")
        parts = normalized.split("/")
        if not normalized or ".." in parts or "." in parts:
            raise ValueError("Unsafe source file path")
        return normalized
