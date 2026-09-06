"""Postgres-backed persistence for a user's ingredient inventory.

`user_ingredient_inventory_backing_store` (a DI provider *function* -- see
di/provides.py) builds a fully-configured IndexedPostgresStore for the
`user_ingredient_inventory` table: each user's inventory is a JSONB list of
ingredient-item dicts, keyed by user_id, no extra indexed columns needed.
UserIngredientInventoryStore itself is a plain class with no SQL, table
names, or JSONB in it -- it's injected with that backing store and only
translates between inventory-shaped method calls and the backing store's
generic get/set.
"""
from __future__ import annotations

from dataclasses import asdict

from async_store.indexed_postgres_store import IndexedPostgresStore
from di import provides
from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory

DEFAULT_TABLE_NAME = "user_ingredient_inventory"
DEFAULT_KEY_COLUMN = "user_id"
DEFAULT_VALUE_COLUMN = "items"


@provides("user_ingredient_inventory_backing_store")
def build_user_ingredient_inventory_backing_store() -> IndexedPostgresStore[list]:
    return IndexedPostgresStore(
        table_name=DEFAULT_TABLE_NAME,
        key_column=DEFAULT_KEY_COLUMN,
        value_column=DEFAULT_VALUE_COLUMN,
    )


@provides("user_ingredient_inventory_store")
class UserIngredientInventoryStore:
    """Get/set a user's full ingredient inventory, and add/remove individual items. No SQL/Postgres details here."""

    def __init__(self, user_ingredient_inventory_backing_store: IndexedPostgresStore):
        self._backing_store = user_ingredient_inventory_backing_store

    async def get_inventory(self, user_id: str) -> UserIngredientInventory:
        """Return the user's inventory, or an empty one if none is stored."""
        raw_items = await self._backing_store.get(user_id)
        if raw_items is None:
            return UserIngredientInventory(user_id=user_id, items=[])
        return UserIngredientInventory(
            user_id=user_id,
            items=[InventoryItem(**item) for item in raw_items],
        )

    async def set_inventory(self, inventory: UserIngredientInventory) -> None:
        """Overwrite the user's entire inventory."""
        await self._backing_store.set(inventory.user_id, [asdict(item) for item in inventory.items])

    async def add_item(self, user_id: str, item: InventoryItem) -> UserIngredientInventory:
        """Add (or replace, by name) a single item in the user's inventory."""
        inventory = await self.get_inventory(user_id)
        remaining = [existing for existing in inventory.items if existing.name.lower() != item.name.lower()]
        remaining.append(item)
        updated = UserIngredientInventory(user_id=user_id, items=remaining)
        await self.set_inventory(updated)
        return updated

    async def remove_item(self, user_id: str, item_name: str) -> UserIngredientInventory:
        """Remove a single item (matched case-insensitively by name) from the user's inventory."""
        inventory = await self.get_inventory(user_id)
        remaining = [existing for existing in inventory.items if existing.name.lower() != item_name.lower()]
        updated = UserIngredientInventory(user_id=user_id, items=remaining)
        await self.set_inventory(updated)
        return updated

    async def close(self) -> None:
        await self._backing_store.close()
