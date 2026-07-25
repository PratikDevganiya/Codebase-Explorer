from types import SimpleNamespace

import git

from backend.ingestion.github_loader import GitHubLoader


def test_file_list_excludes_dependency_lockfiles(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "demo"}')
    (tmp_path / "package-lock.json").write_text('{"packages": {}}')
    (tmp_path / "main.js").write_text("console.log('hello')")

    loader = GitHubLoader(local_path=tmp_path / "clones")
    files = loader.get_file_list(tmp_path, extensions=[".json", ".js"])
    names = {path.name for path in files}

    assert names == {"package.json", "main.js"}


def test_clone_falls_back_to_remote_default_branch(tmp_path, monkeypatch):
    calls = []

    def fake_clone(_url, path, **options):
        calls.append(options)
        if "branch" in options:
            raise git.exc.GitCommandError(
                "clone",
                128,
                stderr="fatal: Remote branch main not found in upstream origin",
            )
        path.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(
            active_branch=SimpleNamespace(name="master"),
            head=SimpleNamespace(
                commit=SimpleNamespace(hexsha="1234567890abcdef")
            ),
        )

    monkeypatch.setattr(
        "backend.ingestion.github_loader.Repo.clone_from",
        fake_clone,
    )
    loader = GitHubLoader(local_path=tmp_path / "clones")

    cloned = loader.clone_repository(
        "https://github.com/example/demo",
        branch="main",
    )

    assert cloned.exists()
    assert calls == [
        {"branch": "main", "depth": 1},
        {"depth": 1},
    ]
