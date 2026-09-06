"""
DI provider for the Postgres-backed store behind
store.user_ingredient_inventory_store.UserIngredientInventoryStore.

Builds a fully-configured IndexedPostgresStore for the
`user_ingredient_inventory` table: each user's inventory is a JSONB list of
already-plain ingredient-item dicts, keyed by user_id, no extra indexed
columns needed. UserIngredientInventoryStore itself does the
InventoryItem <-> dict conversion (via InventoryItem.to_dict/from_dict), so
this backing store just passes plain, already-JSON-able lists straight
through -- no custom serialize/deserialize needed here.
"""
from __future__ import annotations

from async_store.indexed_postgres_store import IndexedPostgresStore
from di import provides

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
