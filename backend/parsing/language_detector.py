"""Language detection shared by ingestion and API features."""

import re
from pathlib import Path
from typing import Optional


EXTENSION_LANGUAGES = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".cs": "csharp",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".ini": "ini",
    ".env": "env",
}

FILENAME_LANGUAGES = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "gemfile": "ruby",
    "rakefile": "ruby",
}


def detect_file_language(file_path: Path, content: str = "") -> str:
    """Detect a file's language independently from its repository."""
    filename_language = FILENAME_LANGUAGES.get(file_path.name.lower())
    if filename_language:
        return filename_language

    extension_language = EXTENSION_LANGUAGES.get(file_path.suffix.lower())
    if extension_language:
        return extension_language

    return detect_code_language(content)


def detect_code_language(code: str, fallback: str = "unknown") -> str:
    """Detect the likely language of a pasted snippet using conservative signals."""
    text = code.strip()
    if not text:
        return fallback

    first_line = text.splitlines()[0].lower()
    shebangs = {
        "python": ("python",),
        "javascript": ("node", "deno"),
        "ruby": ("ruby",),
        "php": ("php",),
        "shell": ("bash", "zsh", "/sh"),
    }
    if first_line.startswith("#!"):
        for language, markers in shebangs.items():
            if any(marker in first_line for marker in markers):
                return language

    patterns = (
        ("python", r"(?m)^\s*(?:async\s+)?def\s+\w+\s*\(|^\s*from\s+[\w.]+\s+import\s+|^\s*import\s+\w+|^\s*class\s+\w+.*:"),
        ("typescript", r"\b(?:interface|type)\s+\w+\s*(?:=|\{)|:\s*(?:string|number|boolean)\b"),
        ("javascript", r"\b(?:const|let|var)\s+\w+\s*=|=>|require\s*\(|\bfunction\s+\w+\s*\("),
        ("java", r"\bpublic\s+(?:static\s+)?(?:class|interface|void)\b|\bSystem\.out\.println\s*\("),
        ("go", r"(?m)^\s*package\s+\w+|^\s*func\s+(?:\([^)]*\)\s*)?\w+\s*\("),
        ("rust", r"\bfn\s+\w+\s*\(|\blet\s+mut\b|\bimpl(?:<[^>]+>)?\s+\w+"),
        ("php", r"<\?php|\bfunction\s+\w+\s*\([^)]*\)\s*\{"),
        ("ruby", r"(?m)^\s*def\s+\w+[!?=]?\s*(?:\([^)]*\))?|^\s*class\s+\w+\s*(?:<\s*\w+)?$"),
        ("csharp", r"\bnamespace\s+\w+|\busing\s+System\s*;|\bConsole\.WriteLine\s*\("),
        ("cpp", r"#include\s*<[^>]+>|\bstd::\w+|\b(?:cout|cin)\s*<<"),
        ("sql", r"(?is)^\s*(?:select|insert\s+into|update|delete\s+from|create\s+table)\b"),
        ("html", r"(?is)^\s*<!doctype\s+html|<html\b|<(?:div|section|main|body)\b"),
        ("css", r"(?s)(?:^|\})\s*[.#]?[a-zA-Z][\w\s.#:[\]=\"'-]*\{[^{}]*:[^{}]*;"),
        ("json", r'(?s)^\s*[\[{]\s*"[^"]+"\s*:'),
    )
    for language, pattern in patterns:
        if re.search(pattern, text):
            return language

    return fallback
