from datetime import datetime, timezone

import pytest

from backend.storage.repository_store import (
    SupabaseRepositoryMetadataStore,
)


class FakeProjectRepository:
    def __init__(self):
        self.rows = {}
        self.next_id = 1

    def list(self):
        return list(self.rows.values())

    def get_by_repository_id(self, repository_id):
        return next(
            (
                row
                for row in self.rows.values()
                if row["repository_id"] == repository_id
            ),
            None,
        )

    def create(self, repository_id, **values):
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": f"project-{self.next_id}",
            "repository_id": repository_id,
            "created_at": now,
            "updated_at": now,
            **values,
        }
        self.next_id += 1
        self.rows[row["id"]] = row
        return row

    def update(self, project_id, **values):
        self.rows[project_id].update(values)
        return self.rows[project_id]

    def delete(self, project_id):
        return self.rows.pop(project_id)


def registry_record(**changes):
    return {
        "repository_id": "repo_123",
        "name": "Demo",
        "source_type": "github",
        "source": "https://github.com/example/demo",
        "branch": "main",
        "status": "ready",
        "files_processed": 3,
        "chunks_created": 7,
        "chunks_indexed": 7,
        **changes,
    }


def test_supabase_store_normalizes_records_and_upserts():
    repository = FakeProjectRepository()
    store = SupabaseRepositoryMetadataStore(repository)

    created = store.upsert(registry_record())
    updated = store.upsert(registry_record(status="failed"))

    assert created["repository_id"] == "repo_123"
    assert created["files_processed"] == 3
    assert updated["status"] == "failed"
    assert len(store.list()) == 1
    assert store.get("repo_123") == updated


def test_supabase_store_requires_identity_fields():
    store = SupabaseRepositoryMetadataStore(FakeProjectRepository())

    with pytest.raises(ValueError, match="repository_id"):
        store.upsert({"name": "Demo", "source_type": "zip"})


def test_supabase_store_deletes_by_repository_id():
    store = SupabaseRepositoryMetadataStore(FakeProjectRepository())
    store.upsert(registry_record())

    deleted = store.delete("repo_123")

    assert deleted["repository_id"] == "repo_123"
    assert store.get("repo_123") is None
    assert store.delete("missing") is None
