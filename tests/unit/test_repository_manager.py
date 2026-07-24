import io
import zipfile

import pytest

from backend.ingestion import repository_manager
from backend.ingestion.repository_manager import (
    extract_zip_safely,
    safe_relative_path,
    save_folder_upload,
)


def test_safe_relative_path_rejects_traversal():
    with pytest.raises(ValueError, match="Unsafe"):
        safe_relative_path("../../secret.txt")


def test_folder_upload_preserves_relative_paths(tmp_path):
    saved = save_folder_upload(
        tmp_path,
        [
            ("demo/src/main.py", io.BytesIO(b"print('hello')")),
            ("demo/web/app.js", io.BytesIO(b"console.log('hello')")),
        ],
    )

    assert len(saved) == 2
    assert (tmp_path / "demo/src/main.py").read_text() == "print('hello')"
    assert (tmp_path / "demo/web/app.js").exists()


def test_folder_upload_reports_configured_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(repository_manager, "MAX_FOLDER_UPLOAD_BYTES", 1024 * 1024)

    with pytest.raises(ValueError, match="1 MB limit"):
        save_folder_upload(
            tmp_path,
            [("demo/main.py", io.BytesIO(b"x" * (1024 * 1024 + 1)))],
        )


def test_zip_extraction_rejects_traversal(tmp_path):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("../outside.py", "print('unsafe')")
    payload.seek(0)

    with pytest.raises(ValueError, match="Unsafe"):
        extract_zip_safely(payload, tmp_path / "extracted")
