"""
In-memory AsyncKVStore implementation: a plain dict behind the same async
interface AsyncPostgresStore/IndexedPostgresStore expose. Nothing about it
is Postgres-specific, so it's a genuine drop-in swap for anything typed
against AsyncKVStore -- useful for tests and for local dev without a real
Postgres instance running.
"""
from __future__ import annotations

from typing import Dict, Generic, Optional, TypeVar

from async_store.async_kv_store import AsyncKVStore

K = TypeVar("K")
V = TypeVar("V")


class InMemoryKVStore(AsyncKVStore[K, V], Generic[K, V]):
    """Process-local, in-memory key-value store. Data does not persist across restarts."""

    def __init__(self):
        self._data: Dict[K, V] = {}

    async def get(self, key: K) -> Optional[V]:
        return self._data.get(key)

    async def set(self, key: K, value: V) -> None:
        self._data[key] = value

    async def delete(self, key: K) -> bool:
        existed = key in self._data
        self._data.pop(key, None)
        return existed

    async def close(self) -> None:
        pass
