"""
DI provider for the Postgres-backed store behind
store.user_ingredient_inventory_store.UserIngredientInventoryStore.

Builds a fully-configured IndexedPostgresStore (a genuine AsyncKVStore
implementation, see async_store/indexed_postgres_store.py) for the
`user_ingredient_inventory` table: each user's inventory is a JSONB list of
ingredient-item dicts, keyed by user_id, no extra indexed columns needed.
Both sides deal in UserIngredientInventory directly (get/set), so this
provider owns the UserIngredientInventory <-> row mapping too, kept
separate from UserIngredientInventoryStore itself, which has no
Postgres-specific code at all -- it depends on the AsyncKVStore interface,
so this Postgres-backed provider could be swapped for an InMemoryKVStore-
backed one (see async_store/in_memory_kv_store.py) with no changes there.

`database_url` is itself a DI-injected parameter (see config/database.py's
provide_database_url), not called directly -- provider function parameters
are injected by name exactly like a class's __init__ params.
"""
from __future__ import annotations

from async_store.indexed_postgres_store import IndexedPostgresStore
from config.database import provide_database_url  # noqa: F401 (registers 'database_url' with DI)
from di import provides
from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory

DEFAULT_TABLE_NAME = "user_ingredient_inventory"
DEFAULT_KEY_COLUMN = "user_id"
DEFAULT_VALUE_COLUMN = "items"


def _inventory_from_row(row: dict) -> UserIngredientInventory:
    return UserIngredientInventory(
        user_id=row[DEFAULT_KEY_COLUMN],
        items=[InventoryItem.from_dict(item) for item in row[DEFAULT_VALUE_COLUMN]],
    )


@provides("user_ingredient_inventory_backing_store")
def build_user_ingredient_inventory_backing_store(database_url) -> IndexedPostgresStore[UserIngredientInventory]:
    return IndexedPostgresStore(
        connection_string=database_url,
        table_name=DEFAULT_TABLE_NAME,
        key_column=DEFAULT_KEY_COLUMN,
        value_column=DEFAULT_VALUE_COLUMN,
        serialize=lambda inventory: [item.to_dict() for item in inventory.items],
        deserialize=_inventory_from_row,
    )
