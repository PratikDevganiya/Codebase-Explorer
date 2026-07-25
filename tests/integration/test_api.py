"""
Integration tests for API endpoints.
"""

import io
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

# API storage is replaced with in-memory fakes in these tests. Provide
# non-secret placeholders before importing the application so CI does not
# require production Supabase credentials during test collection.
os.environ["SUPABASE_URL"] = "https://ci-placeholder.supabase.co"
os.environ["SUPABASE_SECRET_KEY"] = (
    "sb_secret_ci_placeholder_not_a_real_credential"
)


# Mock the initialize_system function before importing app
def mock_initialize_system():
    """Mock system initialization for testing."""
    from backend.retrieval.search import CodeSearchEngine
    from backend.llm.rag_pipeline import RAGPipeline
    from backend.llm.llm_client import MockLLMClient
    from backend.retrieval.indexer import Indexer
    from tests.fakes import InMemoryVectorStore
    import backend.api.main as main_module
    
    # Simple embedding for testing
    class SimpleEmbedding:
        def __init__(self):
            self.dimension = 384
        def get_dimension(self):
            return 384
        def generate_embedding(self, text):
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            return [float(hash_bytes[i % len(hash_bytes)]) / 255.0 for i in range(384)]
        def generate_embeddings(self, texts, batch_size=32, show_progress=True):
            return [self.generate_embedding(t) for t in texts]
    
    embedding_generator = SimpleEmbedding()
    vector_store = InMemoryVectorStore(dimension=384)
    search_engine = CodeSearchEngine(vector_store, embedding_generator)
    llm_client = MockLLMClient()
    rag_pipeline = RAGPipeline(search_engine, llm_client, top_k=5)
    indexer = Indexer(embedding_generator, vector_store)
    
    # Set global variables
    main_module.vector_store = vector_store
    main_module.embedding_generator = embedding_generator
    main_module.search_engine = search_engine
    main_module.rag_pipeline = rag_pipeline
    main_module.indexer = indexer


# Patch before importing app
import backend.api.main
backend.api.main.initialize_system = mock_initialize_system

from backend.api.main import app

client = TestClient(app)

# Initialize system for tests
mock_initialize_system()


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert 'message' in data


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] in {'healthy', 'degraded'}
    assert 'version' in data


def test_stats_endpoint():
    """Test stats endpoint."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert 'indexed_vectors' in data or 'status' in data


def test_query_endpoint():
    """Test query endpoint."""
    payload = {
        "query": "test query",
        "language": "python",
        "top_k": 3
    }
    
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'answer' in data
    assert 'sources' in data


def test_query_endpoint_accepts_multiple_repository_ids():
    response = client.post(
        "/query",
        json={
            "query": "test query",
            "repository_ids": ["repo_alpha", "repo_beta"],
        },
    )

    assert response.status_code == 200
    assert "answer" in response.json()


def test_explain_endpoint():
    """Test explain endpoint."""
    payload = {
        "code": "def test(): pass",
        "language": "python"
    }
    
    response = client.post("/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'explanation' in data


def test_explain_endpoint_detects_language_when_omitted():
    """The UI does not need to ask the user for a snippet language."""
    response = client.post(
        "/explain",
        json={"code": "const greet = (name) => `Hi ${name}`;"},
    )

    assert response.status_code == 200
    assert response.json()["language"] == "javascript"


def test_zip_upload_registers_repository_and_scopes_query(tmp_path, monkeypatch):
    import backend.api.main as main_module
    from tests.fakes import InMemoryRepositoryStore, InMemorySourceStorage

    mock_initialize_system()
    monkeypatch.setattr(main_module.settings, "uploads_path", tmp_path / "uploads")
    monkeypatch.setattr(
        main_module,
        "repository_registry",
        InMemoryRepositoryStore(),
    )
    monkeypatch.setattr(
        main_module,
        "source_storage",
        InMemorySourceStorage(),
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("demo/main.py", "def uploaded_feature(): return 'ready'")

    response = client.post(
        "/repositories/upload",
        data={
            "upload_type": "zip",
            "display_name": "Uploaded Demo",
            "relative_paths": "[]",
        },
        files={"files": ("demo.zip", payload.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    repository_id = response.json()["repository_id"]
    assert repository_id.startswith("repo_")
    listed = client.get("/repositories").json()
    assert listed[0]["name"] == "Uploaded Demo"

    files = client.get(f"/repositories/{repository_id}/files")
    assert files.status_code == 200
    assert files.json()[0]["path"] == "demo/main.py"

    preview = client.get(
        f"/repositories/{repository_id}/file",
        params={"path": "demo/main.py"},
    )
    assert preview.status_code == 200
    assert "uploaded_feature" in preview.json()["content"]

    traversal = client.get(
        f"/repositories/{repository_id}/file",
        params={"path": "../../.env"},
    )
    assert traversal.status_code == 404

    query = client.post(
        "/query",
        json={"query": "uploaded feature", "repository_id": repository_id},
    )
    assert query.status_code == 200
    assert query.json()["num_sources"] == 1

    deleted = client.delete(f"/repositories/{repository_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert deleted.json()["files_deleted"] == 1
    assert client.get("/repositories").json() == []
    assert client.get(f"/repositories/{repository_id}/files").status_code == 404

    missing = client.delete(f"/repositories/{repository_id}")
    assert missing.status_code == 404
