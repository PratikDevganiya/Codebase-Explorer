from backend.storage.source_storage import SupabaseSourceStorage


class FakeBucket:
    def __init__(self):
        self.objects = {}

    def upload(self, path, content, _options):
        self.objects[path] = content

    def list(self, prefix):
        prefix_with_slash = f"{prefix}/" if prefix else ""
        direct = {}
        for path, content in self.objects.items():
            if not path.startswith(prefix_with_slash):
                continue
            remainder = path[len(prefix_with_slash):]
            first, separator, _rest = remainder.partition("/")
            if separator:
                direct[first] = {"name": first, "metadata": None}
            else:
                direct[first] = {
                    "name": first,
                    "metadata": {"size": len(content)},
                }
        return list(direct.values())

    def download(self, path):
        return self.objects[path]

    def remove(self, paths):
        for path in paths:
            self.objects.pop(path, None)


class FakeStorage:
    def __init__(self):
        self.bucket = FakeBucket()

    def from_(self, name):
        assert name == "project-sources"
        return self.bucket


class FakeClient:
    def __init__(self):
        self.storage = FakeStorage()


def test_upload_list_and_read_source_files(tmp_path):
    root = tmp_path / "demo"
    file_path = root / "src" / "main.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("print('ready')", encoding="utf-8")
    storage = SupabaseSourceStorage(FakeClient())

    assert storage.upload_files("repo_1", root, [file_path]) == 1
    listed = storage.list_files("repo_1")

    assert listed[0].path == "src/main.py"
    assert listed[0].size_bytes == len("print('ready')")
    assert storage.read_file("repo_1", "src/main.py") == b"print('ready')"


def test_source_storage_rejects_traversal():
    storage = SupabaseSourceStorage(FakeClient())

    try:
        storage.read_file("repo_1", "../../.env")
        raise AssertionError("Expected unsafe path to be rejected")
    except ValueError as error:
        assert "Unsafe" in str(error)


def test_delete_repository_source_files(tmp_path):
    root = tmp_path / "demo"
    first = root / "src" / "main.py"
    second = root / "README.md"
    first.parent.mkdir(parents=True)
    first.write_text("print('ready')", encoding="utf-8")
    second.write_text("# Demo", encoding="utf-8")
    client = FakeClient()
    storage = SupabaseSourceStorage(client)
    storage.upload_files("repo_1", root, [first, second])
    storage.upload_files("repo_2", root, [second])

    assert storage.delete_repository("repo_1") == 2
    assert storage.list_files("repo_1") == []
    assert len(storage.list_files("repo_2")) == 1
