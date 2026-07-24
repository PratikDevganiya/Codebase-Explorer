from pathlib import Path

import pytest

from backend.parsing.language_detector import (
    detect_code_language,
    detect_file_language,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("service.py", "python"),
        ("App.tsx", "typescript"),
        ("main.go", "go"),
        ("Dockerfile", "dockerfile"),
        ("schema.sql", "sql"),
    ],
)
def test_detects_each_file_from_its_own_name(filename, expected):
    assert detect_file_language(Path(filename)) == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("def greet(name):\n    return f'Hi {name}'", "python"),
        ("interface User { id: number; name: string }", "typescript"),
        ("const greet = (name) => `Hi ${name}`;", "javascript"),
        ("package main\nfunc main() {}", "go"),
        ("SELECT id, name FROM users;", "sql"),
    ],
)
def test_detects_pasted_code_without_a_language_selection(code, expected):
    assert detect_code_language(code) == expected


def test_unknown_snippet_is_not_aggressively_guessed():
    assert detect_code_language("some words without language syntax") == "unknown"
