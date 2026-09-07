"""Tests for InMemoryKVStore: a plain AsyncKVStore[K, V] conformance check."""
import unittest

from async_store.async_kv_store import AsyncKVStore
from async_store.in_memory_kv_store import InMemoryKVStore


class InMemoryKVStoreTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = InMemoryKVStore()

    def test_is_a_genuine_async_kv_store(self):
        self.assertIsInstance(self.store, AsyncKVStore)

    async def test_get_missing_key_returns_none(self):
        self.assertIsNone(await self.store.get("missing"))

    async def test_set_then_get_round_trips(self):
        await self.store.set("a", {"value": 1})
        self.assertEqual(await self.store.get("a"), {"value": 1})

    async def test_set_overwrites_existing_value(self):
        await self.store.set("a", "first")
        await self.store.set("a", "second")
        self.assertEqual(await self.store.get("a"), "second")

    async def test_delete_removes_the_key_and_reports_it_existed(self):
        await self.store.set("a", "value")
        deleted = await self.store.delete("a")
        self.assertTrue(deleted)
        self.assertIsNone(await self.store.get("a"))

    async def test_delete_missing_key_reports_it_did_not_exist(self):
        deleted = await self.store.delete("missing")
        self.assertFalse(deleted)

    async def test_keys_are_isolated_from_each_other(self):
        await self.store.set("a", 1)
        await self.store.set("b", 2)
        self.assertEqual(await self.store.get("a"), 1)
        self.assertEqual(await self.store.get("b"), 2)

    async def test_close_is_a_no_op(self):
        await self.store.set("a", 1)
        await self.store.close()
        # Unlike a real connection-backed store, close() doesn't invalidate
        # further use -- there's no connection to lose.
        self.assertEqual(await self.store.get("a"), 1)


if __name__ == "__main__":
    unittest.main()
