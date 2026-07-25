from types import SimpleNamespace

from backend.llm.gemini_keys import GeminiClientPool
from backend.retrieval.embeddings import EmbeddingGenerator


class MismatchedBatchModels:
    def embed_content(self, *, contents, **_kwargs):
        if isinstance(contents, list):
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.1, 0.2])],
            )
        value = 1.0 if contents == "alpha" else 2.0
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[value, value])],
        )


def test_gemini_batch_count_mismatch_retries_individually():
    generator = EmbeddingGenerator.__new__(EmbeddingGenerator)
    generator.client = SimpleNamespace(models=MismatchedBatchModels())
    generator.model_name = "gemini-embedding-2"
    generator.dimension = 2
    generator.last_error = None

    embeddings = generator._generate_gemini_batch(["alpha", "beta"])

    assert embeddings == [[1.0, 1.0], [2.0, 2.0]]
    assert generator.last_error is None


class QuotaEmbeddingModels:
    def embed_content(self, **_kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")


class SuccessfulEmbeddingModels:
    def __init__(self):
        self.calls = 0

    def embed_content(self, **_kwargs):
        self.calls += 1
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.3, 0.7])],
        )


def test_gemini_embedding_switches_to_backup_key_on_quota():
    primary = SimpleNamespace(models=QuotaEmbeddingModels())
    backup_models = SuccessfulEmbeddingModels()
    backup = SimpleNamespace(models=backup_models)
    clients = {"primary-key": primary, "backup-key": backup}

    generator = EmbeddingGenerator.__new__(EmbeddingGenerator)
    generator._gemini_pool = GeminiClientPool(
        ["primary-key", "backup-key"],
        lambda key: clients[key],
    )
    generator.client = primary
    generator.model_name = "gemini-embedding-2"
    generator.dimension = 2
    generator.last_error = None

    embedding = generator._generate_gemini_embedding("alpha")

    assert embedding == [0.3, 0.7]
    assert backup_models.calls == 1
    assert generator.client is backup
    assert generator._gemini_pool.active_index == 1
