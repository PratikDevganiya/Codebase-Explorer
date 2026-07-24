"""Supabase-backed repository metadata adapter."""

from typing import Any, Dict, List

from backend.storage.project_repository import SupabaseProjectRepository


class SupabaseRepositoryMetadataStore:
    """Expose Supabase rows in the API repository record shape."""

    def __init__(self, repository: SupabaseProjectRepository | None = None):
        self._repository = repository or SupabaseProjectRepository()

    def list(self) -> List[Dict[str, Any]]:
        return [self._to_registry_record(row) for row in self._repository.list()]

    def get(self, repository_id: str) -> Dict[str, Any] | None:
        row = self._repository.get_by_repository_id(repository_id)
        return self._to_registry_record(row) if row else None

    def delete(self, repository_id: str) -> Dict[str, Any] | None:
        row = self._repository.get_by_repository_id(repository_id)
        if row is None:
            return None
        deleted = self._repository.delete(row["id"])
        return self._to_registry_record(deleted)

    def upsert(self, record: Dict[str, Any]) -> Dict[str, Any]:
        repository_id = self._required(record, "repository_id")
        existing = self._repository.get_by_repository_id(repository_id)
        values = self._to_project_values(record)

        if existing:
            row = self._repository.update(existing["id"], **values)
        else:
            row = self._repository.create(
                repository_id=repository_id,
                **values,
            )
        return self._to_registry_record(row)

    @staticmethod
    def _required(record: Dict[str, Any], field: str) -> Any:
        value = record.get(field)
        if value is None or value == "":
            raise ValueError(f"Repository record requires {field}")
        return value

    @classmethod
    def _to_project_values(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": cls._required(record, "name"),
            "source_type": cls._required(record, "source_type"),
            "source_url": record.get("source"),
            "branch": record.get("branch"),
            "status": record.get("status", "pending"),
            "file_count": record.get("files_processed", 0),
            "chunk_count": record.get("chunks_created", 0),
            "indexed_count": record.get("chunks_indexed", 0),
            "error_message": record.get("error_message"),
            "storage_prefix": record.get("storage_prefix"),
        }

    @staticmethod
    def _to_registry_record(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "repository_id": row["repository_id"],
            "name": row["name"],
            "source_type": row["source_type"],
            "source": row.get("source_url") or "",
            "branch": row.get("branch"),
            "status": row["status"],
            "files_processed": row.get("file_count", 0),
            "chunks_created": row.get("chunk_count", 0),
            "chunks_indexed": row.get("indexed_count", 0),
            "error_message": row.get("error_message"),
            "storage_prefix": row.get("storage_prefix"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
