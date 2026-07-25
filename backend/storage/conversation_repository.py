"""Persistent named conversations and their selected project scope."""

from typing import Any, Dict, List
from datetime import datetime, timezone

from backend.storage.supabase_client import get_supabase_client


class SupabaseConversationRepository:
    TABLE_NAME = "conversations"
    PROJECT_TABLE = "conversation_projects"

    def __init__(self, client=None):
        self._client = client or get_supabase_client()

    @staticmethod
    def _normalize_project_ids(repository_ids: List[str]) -> List[str]:
        project_ids = list(dict.fromkeys(repository_ids))
        if not project_ids:
            raise ValueError("A conversation requires at least one project")
        if len(project_ids) > 10:
            raise ValueError("A conversation can include at most 10 projects")
        return project_ids

    def _project_map(self) -> Dict[str, List[str]]:
        response = (
            self._client.table(self.PROJECT_TABLE)
            .select("*")
            .order("position")
            .execute()
        )
        project_map: Dict[str, List[str]] = {}
        for row in response.data or []:
            project_map.setdefault(row["conversation_id"], []).append(
                row["repository_id"]
            )
        return project_map

    def _with_projects(
        self,
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        project_map = self._project_map()
        return [
            {
                **row,
                "repository_ids": project_map.get(row["id"], []),
            }
            for row in rows
        ]

    def list(self) -> List[Dict[str, Any]]:
        response = (
            self._client.table(self.TABLE_NAME)
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
        return self._with_projects(list(response.data or []))

    def get(self, conversation_id: str) -> Dict[str, Any] | None:
        response = (
            self._client.table(self.TABLE_NAME)
            .select("*")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        rows = self._with_projects(list(response.data or []))
        return rows[0] if rows else None

    def create(
        self,
        repository_ids: List[str],
        title: str = "New chat",
    ) -> Dict[str, Any]:
        project_ids = self._normalize_project_ids(repository_ids)
        clean_title = title.strip()[:120] or "New chat"
        response = (
            self._client.table(self.TABLE_NAME)
            .insert({"title": clean_title})
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the conversation")
        conversation = response.data[0]
        self._client.table(self.PROJECT_TABLE).insert([
            {
                "conversation_id": conversation["id"],
                "repository_id": repository_id,
                "position": position,
            }
            for position, repository_id in enumerate(project_ids)
        ]).execute()
        return {**conversation, "repository_ids": project_ids}

    def update(
        self,
        conversation_id: str,
        *,
        title: str | None = None,
        repository_ids: List[str] | None = None,
    ) -> Dict[str, Any] | None:
        updates: Dict[str, Any] = {}
        if title is not None:
            updates["title"] = title.strip()[:120] or "New chat"
        if updates or repository_ids is not None:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            (
                self._client.table(self.TABLE_NAME)
                .update(updates)
                .eq("id", conversation_id)
                .execute()
            )
        if repository_ids is not None:
            project_ids = self._normalize_project_ids(repository_ids)
            (
                self._client.table(self.PROJECT_TABLE)
                .delete()
                .eq("conversation_id", conversation_id)
                .execute()
            )
            self._client.table(self.PROJECT_TABLE).insert([
                {
                    "conversation_id": conversation_id,
                    "repository_id": repository_id,
                    "position": position,
                }
                for position, repository_id in enumerate(project_ids)
            ]).execute()
        return self.get(conversation_id)

    def touch(self, conversation_id: str) -> None:
        (
            self._client.table(self.TABLE_NAME)
            .update({"updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", conversation_id)
            .execute()
        )

    def delete(self, conversation_id: str) -> bool:
        response = (
            self._client.table(self.TABLE_NAME)
            .delete()
            .eq("id", conversation_id)
            .execute()
        )
        return bool(response.data)
