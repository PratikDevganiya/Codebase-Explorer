from types import SimpleNamespace

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
