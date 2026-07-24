"""Safe temporary upload handling."""

import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterable, List
from uuid import uuid4


MAX_FOLDER_UPLOAD_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_BYTES = 250 * 1024 * 1024
MAX_FILES = 2_000


def _format_megabytes(size: int) -> int:
    return size // (1024 * 1024)


def create_repository_id() -> str:
    return f"repo_{uuid4().hex[:16]}"


def safe_relative_path(value: str) -> Path:
    """Return a safe relative path or raise for traversal/absolute paths."""
    normalized = value.replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe upload path: {value}")
    return Path(*path.parts)


def save_folder_upload(
    destination: Path,
    streams: Iterable[tuple[str, BinaryIO]],
) -> List[Path]:
    """Persist browser-selected folder files while preserving relative paths."""
    destination.mkdir(parents=True, exist_ok=True)
    saved = []
    total_size = 0

    for index, (relative_name, stream) in enumerate(streams):
        if index >= MAX_FILES:
            raise ValueError(f"Folder contains more than {MAX_FILES} files")
        relative_path = safe_relative_path(relative_name)
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        with target.open("wb") as output:
            while chunk := stream.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_FOLDER_UPLOAD_BYTES:
                    raise ValueError(
                        "Folder upload exceeds the "
                        f"{_format_megabytes(MAX_FOLDER_UPLOAD_BYTES)} MB limit"
                    )
                output.write(chunk)
        saved.append(target)

    return saved


def extract_zip_safely(archive_stream: BinaryIO, destination: Path) -> List[Path]:
    """Extract a ZIP while preventing traversal, symlinks, and ZIP bombs."""
    destination.mkdir(parents=True, exist_ok=True)
    saved = []

    with zipfile.ZipFile(archive_stream) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if len(members) > MAX_FILES:
            raise ValueError(f"ZIP contains more than {MAX_FILES} files")
        if sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES:
            raise ValueError(
                "Extracted ZIP content exceeds the "
                f"{_format_megabytes(MAX_EXTRACTED_BYTES)} MB limit"
            )

        for member in members:
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("ZIP symlinks are not allowed")
            relative_path = safe_relative_path(member.filename)
            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            saved.append(target)

    return saved
