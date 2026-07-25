from datetime import datetime, timezone
from types import SimpleNamespace

from backend.storage.conversation_repository import (
    SupabaseConversationRepository,
)


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.operation = "select"
        self.payload = None
        self.filters = {}
        self.limit_count = None
        self.order_field = None
        self.descending = False

    def select(self, *_args):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def order(self, field, desc=False):
        self.order_field = field
        self.descending = desc
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def execute(self):
        rows = self.client.tables[self.table]
        matching = [
            row for row in rows
            if all(row.get(field) == value for field, value in self.filters.items())
        ]
        if self.operation == "insert":
            payloads = self.payload if isinstance(self.payload, list) else [self.payload]
            inserted = []
            for payload in payloads:
                now = datetime.now(timezone.utc).isoformat()
                row = {
                    "id": f"conversation-{len(rows) + 1}",
                    "created_at": now,
                    "updated_at": now,
                    **payload,
                } if self.table == "conversations" else dict(payload)
                rows.append(row)
                inserted.append(row)
            return SimpleNamespace(data=inserted)
        if self.operation == "update":
            for row in matching:
                row.update(self.payload)
            return SimpleNamespace(data=matching)
        if self.operation == "delete":
            self.client.tables[self.table] = [
                row for row in rows if row not in matching
            ]
            return SimpleNamespace(data=matching)
        if self.order_field:
            matching.sort(
                key=lambda row: row.get(self.order_field),
                reverse=self.descending,
            )
        if self.limit_count is not None:
            matching = matching[:self.limit_count]
        return SimpleNamespace(data=matching)


class FakeClient:
    def __init__(self):
        self.tables = {
            "conversations": [],
            "conversation_projects": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


def test_conversations_preserve_project_order_and_can_be_updated():
    repository = SupabaseConversationRepository(FakeClient())
    created = repository.create(
        ["repo_2", "repo_1", "repo_2"],
        "Authentication flow",
    )

    assert created["title"] == "Authentication flow"
    assert created["repository_ids"] == ["repo_2", "repo_1"]
    assert repository.list()[0]["repository_ids"] == ["repo_2", "repo_1"]

    updated = repository.update(
        created["id"],
        title="Updated title",
        repository_ids=["repo_1"],
    )
    assert updated["title"] == "Updated title"
    assert updated["repository_ids"] == ["repo_1"]

    assert repository.delete(created["id"]) is True
    assert repository.list() == []

