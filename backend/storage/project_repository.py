"""Persistence operations for project metadata stored in Supabase."""

from typing import Any, Dict, List
from uuid import uuid4

from supabase import Client

from backend.storage.supabase_client import get_supabase_client


class ProjectNotFoundError(LookupError):
    """Raised when a project record does not exist."""


class SupabaseProjectRepository:
    """Read and write project metadata without exposing Supabase to API routes."""

    TABLE_NAME = "projects"
    SOURCE_TYPES = {"github", "folder", "zip"}
    STATUSES = {"pending", "uploading", "indexing", "ready", "failed"}
    MUTABLE_FIELDS = {
        "name",
        "source_type",
        "source_url",
        "branch",
        "status",
        "file_count",
        "chunk_count",
        "indexed_count",
        "error_message",
        "storage_prefix",
    }

    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    def create(
        self,
        *,
        name: str,
        source_type: str,
        repository_id: str | None = None,
        source_url: str | None = None,
        branch: str | None = None,
        status: str = "pending",
        file_count: int = 0,
        chunk_count: int = 0,
        indexed_count: int = 0,
        error_message: str | None = None,
        storage_prefix: str | None = None,
    ) -> Dict[str, Any]:
        """Create and return a project metadata record."""
        self._validate_source_type(source_type)
        self._validate_status(status)
        if not name.strip():
            raise ValueError("Project name cannot be empty")

        payload = {
            "repository_id": repository_id or f"repo_{uuid4().hex[:16]}",
            "name": name.strip(),
            "source_type": source_type,
            "source_url": source_url,
            "branch": branch,
            "status": status,
            "file_count": file_count,
            "chunk_count": chunk_count,
            "indexed_count": indexed_count,
            "error_message": error_message,
            "storage_prefix": storage_prefix,
        }
        response = (
            self._client.table(self.TABLE_NAME)
            .insert(payload)
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the created project")
        return response.data[0]

    def list(self) -> List[Dict[str, Any]]:
        """Return projects with the most recently created first."""
        response = (
            self._client.table(self.TABLE_NAME)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return list(response.data or [])

    def get(self, project_id: str) -> Dict[str, Any] | None:
        """Return one project, or None when it does not exist."""
        response = (
            self._client.table(self.TABLE_NAME)
            .select("*")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_by_repository_id(self, repository_id: str) -> Dict[str, Any] | None:
        """Return a project by its stable application repository identifier."""
        response = (
            self._client.table(self.TABLE_NAME)
            .select("*")
            .eq("repository_id", repository_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def update(self, project_id: str, **changes: Any) -> Dict[str, Any]:
        """Update allowed metadata fields and return the updated project."""
        if not changes:
            raise ValueError("At least one project field must be provided")

        unknown_fields = set(changes) - self.MUTABLE_FIELDS
        if unknown_fields:
            fields = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Unsupported project fields: {fields}")

        if "source_type" in changes:
            self._validate_source_type(changes["source_type"])
        if "status" in changes:
            self._validate_status(changes["status"])
        if "name" in changes:
            if not str(changes["name"]).strip():
                raise ValueError("Project name cannot be empty")
            changes["name"] = str(changes["name"]).strip()

        response = (
            self._client.table(self.TABLE_NAME)
            .update(changes)
            .eq("id", project_id)
            .execute()
        )
        if not response.data:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return response.data[0]

    def delete(self, project_id: str) -> Dict[str, Any]:
        """Delete a project metadata record and return its previous value."""
        project = self.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project not found: {project_id}")

        (
            self._client.table(self.TABLE_NAME)
            .delete()
            .eq("id", project_id)
            .execute()
        )
        return project

    @classmethod
    def _validate_source_type(cls, source_type: str) -> None:
        if source_type not in cls.SOURCE_TYPES:
            allowed = ", ".join(sorted(cls.SOURCE_TYPES))
            raise ValueError(f"source_type must be one of: {allowed}")

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            allowed = ", ".join(sorted(cls.STATUSES))
            raise ValueError(f"status must be one of: {allowed}")
