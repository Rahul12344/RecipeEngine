"""Round-trip tests for `UserIngredientInventoryStore`.

No local Postgres is reachable in this environment (verified with
`pg_isready -h 127.0.0.1 -p 5432`, which returned "no response"), so
`asyncpg` itself is faked here: `asyncpg.create_pool` is patched to return
an in-memory fake pool/connection, and `AsyncPostgresStore` runs completely
unmodified against it. This exercises the real serialization path
(`AsyncPostgresStore._serialize_value` / `_deserialize_value`, i.e. actual
`json.dumps`/`json.loads`) alongside `UserIngredientInventoryStore`'s
get/set/add/remove logic, without requiring a real database.
"""
import unittest
from unittest import mock

from async_store.async_postgres_store import AsyncPostgresStore
from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory
from store.user_ingredient_inventory_store import (
    DEFAULT_KEY_COLUMN,
    DEFAULT_TABLE_NAME,
    DEFAULT_VALUE_COLUMN,
    UserIngredientInventoryStore,
)


class _FakeAsyncpgConnection:
    """Just enough of asyncpg's connection surface for AsyncPostgresStore."""

    def __init__(self, table: dict, value_column: str):
        self._table = table
        self._value_column = value_column

    async def execute(self, query, *args):
        normalized = " ".join(query.split()).upper()
        if normalized.startswith("CREATE TABLE"):
            return "CREATE TABLE"
        if normalized.startswith("INSERT INTO"):
            key, value = args
            self._table[key] = value
            return "INSERT 0 1"
        if normalized.startswith("DELETE FROM"):
            key = args[0]
            existed = key in self._table
            if existed:
                del self._table[key]
            return f"DELETE {1 if existed else 0}"
        raise AssertionError(f"Unexpected query in fake connection: {query}")

    async def fetchrow(self, query, *args):
        key = args[0]
        if key not in self._table:
            return None
        return {self._value_column: self._table[key]}


class _FakeAsyncpgPoolAcquireContext:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAsyncpgPool:
    def __init__(self, table: dict, value_column: str):
        self._connection = _FakeAsyncpgConnection(table, value_column)

    def acquire(self):
        return _FakeAsyncpgPoolAcquireContext(self._connection)

    async def close(self):
        pass


class UserIngredientInventoryStoreRoundTripTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._table = {}

        async def fake_create_pool(_connection_string):
            return _FakeAsyncpgPool(self._table, DEFAULT_VALUE_COLUMN)

        patcher = mock.patch(
            "async_store.async_postgres_store.asyncpg.create_pool",
            side_effect=fake_create_pool,
        )
        self._mock_create_pool = patcher.start()
        self.addAsyncCleanup(patcher.stop)

        # Mirror the exact table/column configuration
        # UserIngredientInventoryStore uses in production, so the fake pool
        # (keyed on DEFAULT_VALUE_COLUMN above) matches what AsyncPostgresStore
        # actually asks for.
        postgres_store = AsyncPostgresStore(
            connection_string="postgresql://fake/db",
            table_name=DEFAULT_TABLE_NAME,
            key_column=DEFAULT_KEY_COLUMN,
            value_column=DEFAULT_VALUE_COLUMN,
        )
        self.store = UserIngredientInventoryStore(kv_store=postgres_store)
        self.addAsyncCleanup(self.store.close)

    async def test_missing_user_returns_empty_inventory(self):
        inventory = await self.store.get_inventory("nobody")
        self.assertEqual(inventory, UserIngredientInventory(user_id="nobody", items=[]))

    async def test_set_then_get_round_trips(self):
        inventory = UserIngredientInventory(
            user_id="u1",
            items=[
                InventoryItem(name="egg", quantity=6, unit="count"),
                InventoryItem(name="flour", quantity=2.5, unit="cup"),
            ],
        )
        await self.store.set_inventory(inventory)
        result = await self.store.get_inventory("u1")
        self.assertEqual(result, inventory)

    async def test_add_item_appends_and_replaces_existing_by_name(self):
        await self.store.add_item("u1", InventoryItem(name="egg", quantity=6, unit="count"))
        await self.store.add_item("u1", InventoryItem(name="milk", quantity=1, unit="l"))
        # Adding an item with the same name (case-insensitively) replaces it.
        updated = await self.store.add_item("u1", InventoryItem(name="EGG", quantity=12, unit="count"))

        quantities_by_name = {item.name: item.quantity for item in updated.items}
        self.assertEqual(quantities_by_name, {"milk": 1, "EGG": 12})

    async def test_remove_item(self):
        await self.store.add_item("u1", InventoryItem(name="egg", quantity=6, unit="count"))
        await self.store.add_item("u1", InventoryItem(name="milk", quantity=1, unit="l"))

        updated = await self.store.remove_item("u1", "egg")

        self.assertEqual([item.name for item in updated.items], ["milk"])

    async def test_remove_item_is_case_insensitive(self):
        await self.store.add_item("u1", InventoryItem(name="Egg", quantity=6, unit="count"))
        updated = await self.store.remove_item("u1", "EGG")
        self.assertEqual(updated.items, [])

    async def test_inventories_for_different_users_are_isolated(self):
        await self.store.add_item("u1", InventoryItem(name="egg", quantity=6, unit="count"))
        await self.store.add_item("u2", InventoryItem(name="milk", quantity=1, unit="l"))

        u1_inventory = await self.store.get_inventory("u1")
        u2_inventory = await self.store.get_inventory("u2")

        self.assertEqual([item.name for item in u1_inventory.items], ["egg"])
        self.assertEqual([item.name for item in u2_inventory.items], ["milk"])

    async def test_pool_is_created_once_and_reused_across_calls(self):
        await self.store.get_inventory("a")
        await self.store.get_inventory("b")
        self.assertEqual(self._mock_create_pool.call_count, 1)


if __name__ == "__main__":
    unittest.main()
