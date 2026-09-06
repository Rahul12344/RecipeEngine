"""Postgres-backed persistence for a user's ingredient inventory.

Built on top of the existing `AsyncPostgresStore` (async_store/async_postgres_store.py)
rather than hand-rolling new SQL: each user's inventory is stored as a JSONB
list of ingredient-item dicts in its own table, keyed by `user_id`.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from typing import Optional

from async_store.async_kv_store import AsyncKVStore
from async_store.async_postgres_store import AsyncPostgresStore
from di import provides
from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory

DEFAULT_TABLE_NAME = "user_ingredient_inventory"
DEFAULT_KEY_COLUMN = "user_id"
DEFAULT_VALUE_COLUMN = "items"
CONNECTION_STRING_ENV_VAR = "RECIPE_ENGINE_POSTGRES_DSN"
DEFAULT_CONNECTION_STRING = "postgresql://localhost:5432/recipe_engine"


@provides("user_ingredient_inventory_store")
class UserIngredientInventoryStore:
    """Get/set a user's full ingredient inventory, and add/remove individual items.

    Accepts an optional pre-built `AsyncKVStore` so tests (or callers with
    a differently-configured pool) can inject their own -- by default it
    builds an `AsyncPostgresStore` pointed at its own `user_ingredient_inventory`
    table.
    """

    def __init__(self, kv_store: Optional[AsyncKVStore[str, list]] = None):
        self._kv_store: AsyncKVStore[str, list] = kv_store or AsyncPostgresStore(
            connection_string=os.environ.get(CONNECTION_STRING_ENV_VAR, DEFAULT_CONNECTION_STRING),
            table_name=DEFAULT_TABLE_NAME,
            key_column=DEFAULT_KEY_COLUMN,
            value_column=DEFAULT_VALUE_COLUMN,
        )

    async def get_inventory(self, user_id: str) -> UserIngredientInventory:
        """Return the user's inventory, or an empty one if none is stored."""
        raw_items = await self._kv_store.get(user_id)
        if raw_items is None:
            return UserIngredientInventory(user_id=user_id, items=[])
        return UserIngredientInventory(
            user_id=user_id,
            items=[InventoryItem(**item) for item in raw_items],
        )

    async def set_inventory(self, inventory: UserIngredientInventory) -> None:
        """Overwrite the user's entire inventory."""
        await self._kv_store.set(inventory.user_id, [asdict(item) for item in inventory.items])

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
        await self._kv_store.close()
