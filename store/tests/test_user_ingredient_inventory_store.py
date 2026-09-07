"""Round-trip tests for `UserIngredientInventoryStore`.

No local Postgres is reachable in this environment (verified with
`pg_isready -h 127.0.0.1 -p 5432`, which returned "no response"), so this
uses the same `FakeAsyncpgPool` as RecipeStore/RecipeAnnotationStore (see
store/tests/fake_asyncpg.py) rather than a real database: `asyncpg` itself
is faked, and `AsyncPostgresStore` (via `IndexedPostgresStore`) runs
completely unmodified against it, exercising the real serialize/deserialize
path alongside `UserIngredientInventoryStore`'s get/set/add/remove logic.
"""
import unittest
from unittest import mock
from unittest.mock import AsyncMock

from async_store.in_memory_kv_store import InMemoryKVStore
from di import container, reset_container
from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory
from store.postgres.user_ingredient_inventory_backing_store import build_user_ingredient_inventory_backing_store  # noqa: F401 (registers with DI)
from store.tests.fake_asyncpg import FakeAsyncpgPool
from store.user_ingredient_inventory_store import UserIngredientInventoryStore


class UserIngredientInventoryStoreRoundTripTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake_pool = FakeAsyncpgPool()
        self._patcher = mock.patch(
            "async_store.async_postgres_store.asyncpg.create_pool",
            new=AsyncMock(return_value=self.fake_pool),
        )
        self._mock_create_pool = self._patcher.start()
        self.addAsyncCleanup(self._patcher.stop)

        self._env_patcher = mock.patch.dict(
            "os.environ", {"RECIPE_ENGINE_DATABASE_URL": "postgresql://fake/db"}
        )
        self._env_patcher.start()
        self.addAsyncCleanup(self._env_patcher.stop)

        # Resolved through the real DI container end to end
        # (UserIngredientInventoryStore <- user_ingredient_inventory_backing_store
        # <- database_url), not hand-assembled, so a regression anywhere in
        # that chain would show up here too.
        reset_container()
        self.addAsyncCleanup(reset_container)
        self.store = container().get(UserIngredientInventoryStore)

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


class UserIngredientInventoryStoreWithInMemoryBackingStoreTest(unittest.IsolatedAsyncioTestCase):
    """UserIngredientInventoryStore depends on the AsyncKVStore interface, not
    IndexedPostgresStore specifically -- proves the backing store is a real,
    swappable dependency by running the same scenarios as the Postgres-backed
    tests above against a plain InMemoryKVStore instead, no DI/Postgres/fakes
    involved at all."""

    async def asyncSetUp(self):
        self.store = UserIngredientInventoryStore(user_ingredient_inventory_backing_store=InMemoryKVStore())

    async def test_missing_user_returns_empty_inventory(self):
        inventory = await self.store.get_inventory("nobody")
        self.assertEqual(inventory, UserIngredientInventory(user_id="nobody", items=[]))

    async def test_set_then_get_round_trips(self):
        inventory = UserIngredientInventory(
            user_id="u1",
            items=[InventoryItem(name="egg", quantity=6, unit="count")],
        )
        await self.store.set_inventory(inventory)
        self.assertEqual(await self.store.get_inventory("u1"), inventory)

    async def test_add_and_remove_item(self):
        await self.store.add_item("u1", InventoryItem(name="egg", quantity=6, unit="count"))
        await self.store.add_item("u1", InventoryItem(name="milk", quantity=1, unit="l"))
        updated = await self.store.remove_item("u1", "egg")
        self.assertEqual([item.name for item in updated.items], ["milk"])

    async def test_inventories_for_different_users_are_isolated(self):
        await self.store.add_item("u1", InventoryItem(name="egg", quantity=6, unit="count"))
        await self.store.add_item("u2", InventoryItem(name="milk", quantity=1, unit="l"))

        self.assertEqual([item.name for item in (await self.store.get_inventory("u1")).items], ["egg"])
        self.assertEqual([item.name for item in (await self.store.get_inventory("u2")).items], ["milk"])


class UserIngredientInventoryStoreConfigTest(unittest.IsolatedAsyncioTestCase):
    """RECIPE_ENGINE_DATABASE_URL is shared with RecipeStore/RecipeAnnotationStore --
    all three stores live in the same Postgres database, just different tables."""

    async def test_missing_connection_string_raises_a_clear_error(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            reset_container()
            store = container().get(UserIngredientInventoryStore)
            with self.assertRaises(RuntimeError):
                await store.get_inventory("anyone")
        reset_container()

    async def test_database_url_is_injected_from_the_shared_env_var(self):
        """Confirms the DI wiring end to end: config.database.provide_database_url
        (tested on its own in config/tests/test_database.py) actually reaches
        this store's backing store via injection, not a direct call."""
        with mock.patch.dict("os.environ", {"RECIPE_ENGINE_DATABASE_URL": "postgresql://x/y"}):
            reset_container()
            store = container().get(UserIngredientInventoryStore)
            self.assertEqual(store._backing_store.connection_string, "postgresql://x/y")
        reset_container()


if __name__ == "__main__":
    unittest.main()
