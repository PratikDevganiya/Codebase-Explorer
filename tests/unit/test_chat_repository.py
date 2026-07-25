from types import SimpleNamespace

from backend.storage.chat_repository import SupabaseChatRepository


class FakeChatQuery:
    def __init__(self, client):
        self.client = client
        self.payload = None
        self.filters = {}
        self.operation = "select"

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def select(self, *_args):
        self.operation = "select"
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def order(self, _field):
        return self

    def execute(self):
        if self.operation == "insert":
            row = {
                "id": f"message-{len(self.client.rows) + 1}",
                "created_at": "2026-07-24T00:00:00+00:00",
                **self.payload,
            }
            self.client.rows.append(row)
            return SimpleNamespace(data=[row])

        matching = [
            row for row in self.client.rows
            if all(row[field] == value for field, value in self.filters.items())
        ]
        if self.operation == "delete":
            self.client.rows = [
                row for row in self.client.rows if row not in matching
            ]
        if self.operation == "update":
            for row in matching:
                row.update(self.payload)
        return SimpleNamespace(data=matching)


class FakeChatClient:
    def __init__(self):
        self.rows = []

    def table(self, name):
        assert name == "chat_messages"
        return FakeChatQuery(self)


def test_chat_history_is_scoped_and_clearable():
    repository = SupabaseChatRepository(FakeChatClient())
    repository.append(
        repository_id="repo_1",
        session_id="00000000-0000-0000-0000-000000000001",
        role="user",
        content="How does this work?",
    )
    repository.append(
        repository_id="repo_2",
        session_id="00000000-0000-0000-0000-000000000001",
        role="assistant",
        content="A different project",
    )

    messages = repository.list(
        "repo_1",
        "00000000-0000-0000-0000-000000000001",
    )
    assert [message["content"] for message in messages] == [
        "How does this work?"
    ]

    repository.clear(
        "repo_1",
        "00000000-0000-0000-0000-000000000001",
    )
    assert repository.list(
        "repo_1",
        "00000000-0000-0000-0000-000000000001",
    ) == []


def test_chat_history_can_be_scoped_to_a_named_conversation():
    repository = SupabaseChatRepository(FakeChatClient())
    repository.append(
        repository_id="repo_1",
        session_id="00000000-0000-0000-0000-000000000001",
        conversation_id="conversation-1",
        role="user",
        content="Explain authentication",
    )

    messages = repository.list_conversation("conversation-1")
    assert [message["content"] for message in messages] == [
        "Explain authentication"
    ]

    repository.reassign_conversation_repository("conversation-1", "repo_2")
    assert repository.list_conversation("conversation-1")[0]["repository_id"] == "repo_2"

    repository.clear_conversation("conversation-1")
    assert repository.list_conversation("conversation-1") == []
