import pytest

from backend.parsing.chunker import CodeChunk
from backend.retrieval.indexer import Indexer
from tests.fakes import InMemoryVectorStore


class PartiallyFailingEmbedding:
    last_error = "Gemini returned malformed output"

    def generate_embeddings(self, texts, batch_size=32):
        return [[0.1] * 384, None]


def test_indexer_rejects_partial_embedding_results():
    store = InMemoryVectorStore(dimension=384)
    chunks = [
        CodeChunk(content="alpha", metadata={"repository_id": "repo_one"}),
        CodeChunk(content="beta", metadata={"repository_id": "repo_one"}),
    ]

    with pytest.raises(RuntimeError, match="Gemini returned malformed output"):
        Indexer(PartiallyFailingEmbedding(), store).index_chunks(chunks)

    assert store.vectors == []
