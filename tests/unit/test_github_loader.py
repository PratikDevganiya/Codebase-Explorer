from backend.ingestion.github_loader import GitHubLoader


def test_file_list_excludes_dependency_lockfiles(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "demo"}')
    (tmp_path / "package-lock.json").write_text('{"packages": {}}')
    (tmp_path / "main.js").write_text("console.log('hello')")

    loader = GitHubLoader(local_path=tmp_path / "clones")
    files = loader.get_file_list(tmp_path, extensions=[".json", ".js"])
    names = {path.name for path in files}

    assert names == {"package.json", "main.js"}
