"""Shared Gemini API-key failover helpers."""

from __future__ import annotations

import os
from threading import RLock
from typing import Callable, Generic, Iterator, TypeVar


ClientT = TypeVar("ClientT")
INVALID_KEYS = {"", "your_gemini_api_key_here"}


def configured_gemini_keys(explicit_key: str | None = None) -> list[str]:
    """Return unique Gemini keys without logging or exposing their values."""
    candidates = [
        explicit_key
        if explicit_key is not None
        else os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GEMINI_API_KEY_BACKUP", ""),
    ]
    keys: list[str] = []
    for candidate in candidates:
        key = (candidate or "").strip()
        if key in INVALID_KEYS or key in keys:
            continue
        keys.append(key)
    return keys


def is_gemini_quota_error(error: Exception | str) -> bool:
    """Return whether Gemini explicitly reported an exhausted quota."""
    message = str(error).upper()
    return "429" in message or "RESOURCE_EXHAUSTED" in message


class GeminiClientPool(Generic[ClientT]):
    """Lazily create Gemini clients and retain the last successful key."""

    def __init__(
        self,
        keys: list[str],
        client_factory: Callable[[str], ClientT],
    ):
        if not keys:
            raise ValueError("At least one Gemini API key is required")
        self._keys = keys
        self._client_factory = client_factory
        self._clients: dict[int, ClientT] = {}
        self._active_index = 0
        self._lock = RLock()

    @property
    def key_count(self) -> int:
        return len(self._keys)

    @property
    def active_index(self) -> int:
        with self._lock:
            return self._active_index

    def client(self, index: int) -> ClientT:
        with self._lock:
            if index not in self._clients:
                self._clients[index] = self._client_factory(self._keys[index])
            return self._clients[index]

    def active_client(self) -> ClientT:
        return self.client(self.active_index)

    def candidates(self) -> Iterator[tuple[int, ClientT]]:
        """Yield every configured key once, starting with the active key."""
        start = self.active_index
        for offset in range(self.key_count):
            index = (start + offset) % self.key_count
            yield index, self.client(index)

    def activate(self, index: int) -> ClientT:
        with self._lock:
            self._active_index = index
        return self.client(index)
