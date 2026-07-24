from types import SimpleNamespace

import pytest

from backend.retrieval.vector_store import SupabaseVectorStore


class FakeSupabaseQuery:
    def __init__(self, client):
        self.client = client

    def upsert(self, rows):
        self.client.rows.extend(rows)
        return self

    def select(self, *_args, **_kwargs):
        return self

    def limit(self, _value):
        return self

    def execute(self):
        return SimpleNamespace(data=[], count=len(self.client.rows))


class FakeSupabaseVectorClient:
    def __init__(self):
        self.rows = []
        self.rpc_payload = None

    def table(self, name):
        assert name == "code_chunks"
        return FakeSupabaseQuery(self)

    def rpc(self, name, payload):
        assert name == "match_code_chunks"
        self.rpc_payload = payload
        return SimpleNamespace(
            execute=lambda: SimpleNamespace(data=[{
                "id": "chunk-1",
                "distance": 0.25,
                "metadata": {"repository_id": "repo_1"},
            }])
        )


def test_supabase_vector_store_adds_searches_and_reports_stats():
    client = FakeSupabaseVectorClient()
    store = SupabaseVectorStore(384, client=client)
    vector = [0.1] * 384

    store.add_vectors(
        [vector],
        [{"repository_id": "repo_1", "content": "hello"}],
        ["chunk-1"],
    )
    results = store.search(
        vector,
        k=5,
        filter_dict={"repository_id": "repo_1"},
    )

    assert client.rows[0]["id"] == "chunk-1"
    assert client.rpc_payload["metadata_filter"] == {
        "repository_id": "repo_1"
    }
    assert results[0]["score"] == 0.25
    assert store.get_stats()["total_vectors"] == 1


def test_supabase_vector_store_requires_matching_dimensions():
    with pytest.raises(ValueError, match="384-dimensional"):
        SupabaseVectorStore(1536, client=FakeSupabaseVectorClient())
