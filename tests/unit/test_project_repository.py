from types import SimpleNamespace

import pytest

from backend.storage.project_repository import (
    ProjectNotFoundError,
    SupabaseProjectRepository,
)


class FakeQuery:
    def __init__(self, client, operation, payload=None):
        self.client = client
        self.operation = operation
        self.payload = payload
        self.filter_field = None
        self.filter_value = None

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
        self.filter_field = field
        self.filter_value = value
        return self

    def limit(self, _value):
        return self

    def order(self, _field, desc=False):
        self.client.ordered_desc = desc
        return self

    def execute(self):
        if self.operation == "insert":
            record = {
                "id": "project-1",
                "file_count": 0,
                "chunk_count": 0,
                "indexed_count": 0,
                **self.payload,
            }
            self.client.records[record["id"]] = record
            return SimpleNamespace(data=[record])

        if self.operation == "select":
            if self.filter_field == "id":
                record = self.client.records.get(self.filter_value)
                return SimpleNamespace(data=[record] if record else [])
            if self.filter_field == "repository_id":
                record = next(
                    (
                        item
                        for item in self.client.records.values()
                        if item["repository_id"] == self.filter_value
                    ),
                    None,
                )
                return SimpleNamespace(data=[record] if record else [])
            return SimpleNamespace(data=list(self.client.records.values()))

        if self.operation == "update":
            record = self.client.records.get(self.filter_value)
            if record is None:
                return SimpleNamespace(data=[])
            record.update(self.payload)
            return SimpleNamespace(data=[record])

        if self.operation == "delete":
            record = self.client.records.pop(self.filter_value, None)
            return SimpleNamespace(data=[record] if record else [])

        raise AssertionError(f"Unexpected operation: {self.operation}")


class FakeSupabaseClient:
    def __init__(self):
        self.records = {}
        self.ordered_desc = False

    def table(self, name):
        assert name == "projects"
        return FakeQuery(self, "table")


@pytest.fixture
def repository():
    return SupabaseProjectRepository(FakeSupabaseClient())


def test_create_project(repository):
    project = repository.create(
        name=" Demo ",
        source_type="github",
        source_url="https://github.com/example/demo",
        branch="main",
    )

    assert project["name"] == "Demo"
    assert project["status"] == "pending"
    assert project["file_count"] == 0


def test_list_and_get_projects(repository):
    created = repository.create(name="Demo", source_type="folder")

    assert repository.list() == [created]
    assert repository.get(created["id"]) == created
    assert repository.get("missing") is None
    assert repository.get_by_repository_id(created["repository_id"]) == created


def test_update_project(repository):
    created = repository.create(name="Demo", source_type="zip")

    updated = repository.update(
        created["id"],
        status="ready",
        file_count=4,
        chunk_count=8,
        indexed_count=8,
    )

    assert updated["status"] == "ready"
    assert updated["file_count"] == 4


def test_update_rejects_unknown_fields(repository):
    with pytest.raises(ValueError, match="Unsupported project fields"):
        repository.update("project-1", id="replacement")


def test_delete_project(repository):
    created = repository.create(name="Demo", source_type="folder")

    assert repository.delete(created["id"]) == created
    assert repository.get(created["id"]) is None

    with pytest.raises(ProjectNotFoundError):
        repository.delete(created["id"])


@pytest.mark.parametrize("source_type", ["local", "remote", ""])
def test_create_rejects_invalid_source_type(repository, source_type):
    with pytest.raises(ValueError, match="source_type must be one of"):
        repository.create(name="Demo", source_type=source_type)


def test_update_missing_project_raises(repository):
    with pytest.raises(ProjectNotFoundError):
        repository.update("missing", status="failed")
