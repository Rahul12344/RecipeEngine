"""Persistence for a user's ingredient inventory.

This class has no Postgres-specific code at all, and doesn't even depend on
Postgres being the backing technology: it's injected (via DI) with anything
conforming to the generic AsyncKVStore[str, UserIngredientInventory]
interface (async_store/async_kv_store.py) and just delegates through
get/set. This store has no extra indexed columns, so the plain AsyncKVStore
contract is all it needs -- unlike RecipeStore/RecipeAnnotationStore, it
doesn't require IndexedPostgresStore's richer get_by_column/list. That
means whatever's registered for "user_ingredient_inventory_backing_store"
can be swapped between IndexedPostgresStore (see
store/postgres/user_ingredient_inventory_backing_store.py) and an
InMemoryKVStore (async_store/in_memory_kv_store.py) purely via DI, with
zero changes here.
"""
from __future__ import annotations

from async_store.async_kv_store import AsyncKVStore
from di import provides
from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory


@provides("user_ingredient_inventory_store")
class UserIngredientInventoryStore:
    """Get/set a user's full ingredient inventory, and add/remove individual items. No SQL/Postgres details here."""

    def __init__(self, user_ingredient_inventory_backing_store: AsyncKVStore):
        self._backing_store = user_ingredient_inventory_backing_store

    async def get_inventory(self, user_id: str) -> UserIngredientInventory:
        """Return the user's inventory, or an empty one if none is stored."""
        inventory = await self._backing_store.get(user_id)
        return inventory if inventory is not None else UserIngredientInventory(user_id=user_id, items=[])

    async def set_inventory(self, inventory: UserIngredientInventory) -> None:
        """Overwrite the user's entire inventory."""
        await self._backing_store.set(inventory.user_id, inventory)

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
