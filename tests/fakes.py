from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.storage.source_storage import StoredSourceFile


class InMemoryVectorStore:
    def __init__(self, dimension=384):
        self.dimension = dimension
        self.vectors = []
        self.metadata = []

    def add_vectors(self, vectors, metadata, ids=None):
        self.vectors.extend(vectors)
        self.metadata.extend(metadata)

    def search(self, query_vector, k=5, filter_dict=None):
        results = []
        query = np.asarray(query_vector, dtype=np.float32)
        for index, (vector, metadata) in enumerate(
            zip(self.vectors, self.metadata)
        ):
            if filter_dict and any(
                metadata.get(key) != value
                for key, value in filter_dict.items()
            ):
                continue
            distance = float(
                np.linalg.norm(np.asarray(vector, dtype=np.float32) - query)
            )
            results.append({
                "index": index,
                "score": distance,
                "metadata": metadata,
            })
        return sorted(results, key=lambda item: item["score"])[:k]

    def save(self, _path):
        return None

    def load(self, _path):
        return None

    def get_stats(self):
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "metadata_count": len(self.metadata),
        }


class InMemoryRepositoryStore:
    def __init__(self):
        self.records = {}

    def list(self):
        return list(self.records.values())

    def get(self, repository_id):
        return self.records.get(repository_id)

    def upsert(self, record):
        now = datetime.now(timezone.utc).isoformat()
        saved = {
            **record,
            "created_at": record.get("created_at", now),
            "updated_at": now,
        }
        self.records[saved["repository_id"]] = saved
        return saved

    def delete(self, repository_id):
        return self.records.pop(repository_id, None)


class InMemorySourceStorage:
    def __init__(self):
        self.objects = {}

    def upload_files(self, repository_id, root, files):
        for file_path in files:
            relative = file_path.resolve().relative_to(
                root.resolve()
            ).as_posix()
            self.objects[(repository_id, relative)] = file_path.read_bytes()
        return len(files)

    def list_files(self, repository_id):
        return sorted(
            [
                StoredSourceFile(path=path, size_bytes=len(content))
                for (stored_repository_id, path), content in self.objects.items()
                if stored_repository_id == repository_id
            ],
            key=lambda item: item.path,
        )

    def read_file(self, repository_id, path):
        return self.objects[(repository_id, path)]

    def delete_repository(self, repository_id):
        keys = [
            key for key in self.objects
            if key[0] == repository_id
        ]
        for key in keys:
            del self.objects[key]
        return len(keys)
