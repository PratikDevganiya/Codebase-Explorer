"""Supabase pgvector storage for code embeddings."""

from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from backend.storage.supabase_client import get_supabase_client
from backend.utils import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Interface used by indexing and retrieval."""

    def add_vectors(
        self,
        vectors: List[List[float]],
        metadata: List[Dict],
        ids: Optional[List[str]] = None,
    ):
        raise NotImplementedError

    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict]:
        raise NotImplementedError

    def save(self, path: Path):
        raise NotImplementedError

    def load(self, path: Path):
        raise NotImplementedError


class SupabaseVectorStore(VectorStore):
    """Persistent vector store backed by Supabase Postgres and pgvector."""

    TABLE_NAME = "code_chunks"
    MATCH_FUNCTION = "match_code_chunks"

    def __init__(self, dimension: int, client=None):
        if dimension != 384:
            raise ValueError(
                "The current Supabase schema uses 384-dimensional vectors"
            )
        self.client = client or get_supabase_client()
        self.dimension = dimension
        logger.info(
            f"SupabaseVectorStore initialized (dimension={dimension})"
        )

    def add_vectors(
        self,
        vectors: List[List[float]],
        metadata: List[Dict],
        ids: Optional[List[str]] = None,
    ):
        if len(vectors) != len(metadata):
            raise ValueError("Vectors and metadata must have the same length")
        if not vectors:
            return

        vector_ids = ids or [str(uuid4()) for _ in vectors]
        rows = [
            {
                "id": vector_id,
                "repository_id": item.get("repository_id"),
                "embedding": vector,
                "metadata": item,
            }
            for vector_id, vector, item in zip(vector_ids, vectors, metadata)
        ]
        for start in range(0, len(rows), 100):
            (
                self.client.table(self.TABLE_NAME)
                .upsert(rows[start:start + 100])
                .execute()
            )
        logger.info(f"Added {len(rows)} vectors to Supabase")

    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict]:
        response = self.client.rpc(
            self.MATCH_FUNCTION,
            {
                "query_embedding": query_vector,
                "match_count": k,
                "metadata_filter": filter_dict or {},
            },
        ).execute()
        return [
            {
                "id": row["id"],
                "score": float(row["distance"]),
                "metadata": row["metadata"],
            }
            for row in (response.data or [])
        ]

    def delete_repository(self, repository_id: str) -> None:
        (
            self.client.table(self.TABLE_NAME)
            .delete()
            .eq("repository_id", repository_id)
            .execute()
        )

    def save(self, path: Path):
        """Cloud vectors are persisted automatically."""

    def load(self, path: Path):
        """Cloud vectors are queried remotely."""

    def get_stats(self) -> Dict:
        response = (
            self.client.table(self.TABLE_NAME)
            .select("id", count="exact")
            .limit(1)
            .execute()
        )
        return {
            "total_vectors": response.count or 0,
            "dimension": self.dimension,
            "metadata_count": response.count or 0,
            "embedding_model": "remote",
        }
