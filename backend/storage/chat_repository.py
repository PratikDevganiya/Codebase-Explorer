"""Project-scoped chat history persistence."""

from typing import Any, Dict, List

from backend.storage.supabase_client import get_supabase_client


class SupabaseChatRepository:
    TABLE_NAME = "chat_messages"
    ROLES = {"user", "assistant"}

    def __init__(self, client=None):
        self._client = client or get_supabase_client()

    def append(
        self,
        *,
        repository_id: str,
        session_id: str,
        role: str,
        content: str,
        sources: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        if role not in self.ROLES:
            raise ValueError("Chat role must be user or assistant")
        if not content.strip():
            raise ValueError("Chat content cannot be empty")

        response = (
            self._client.table(self.TABLE_NAME)
            .insert({
                "repository_id": repository_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "sources": sources or [],
            })
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the chat message")
        return response.data[0]

    def list(
        self,
        repository_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        response = (
            self._client.table(self.TABLE_NAME)
            .select("*")
            .eq("repository_id", repository_id)
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return list(response.data or [])

    def clear(self, repository_id: str, session_id: str) -> None:
        (
            self._client.table(self.TABLE_NAME)
            .delete()
            .eq("repository_id", repository_id)
            .eq("session_id", session_id)
            .execute()
        )
