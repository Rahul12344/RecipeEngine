"""
Shared plumbing for a Postgres-backed store of values of type T, identified
by a string key, with a handful of extra, independently-queryable columns
alongside a JSONB blob holding T's serialized structure.

Both reads and writes deal in T directly: `set(key, value: T)` (always an
upsert) and `get(key) -> Optional[T]` (no separate "row" shape in the public
API) -- the same signatures AsyncKVStore declares, so this is a genuine,
swappable AsyncKVStore[str, T] implementation (see
async_store/in_memory_kv_store.py for another). How T maps onto the table's
columns is entirely a per-implementation concern, supplied at construction
time:
  - `extra_columns`: IndexedColumn(name, extract, ...) entries -- `extract`
    pulls that column's value off a T instance, for writes.
  - `serialize(value: T)`: the JSON-able blob for the value column.
  - `deserialize(row)`: given the *whole* row as a plain dict (every column,
    with the value column already json.loads'd), reconstructs T -- so a
    store whose T needs data from an extra column, not just the blob
    (e.g. StoredRecipe needing `source`/`url`/`ingested_at`), can use it.

This is meant to be used directly (via composition), not subclassed: a
@provides-registered *function* builds a fully-configured instance (table
name, extra columns, serialize/deserialize) for a given entity type, and a
plain, backend-agnostic domain class (e.g. RecipeStore) is injected with
that instance and calls only its generic, non-SQL methods -- no SQL, table
names, or JSONB casting ever appear in a domain class.

This class has no idea where `connection_string` comes from -- that's the
caller's job (see config/database.py's provide_database_url, which the
store/postgres/*_backing_store.py provider functions call directly).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Generic, List, NamedTuple, Optional, Sequence, TypeVar

from async_store.async_postgres_store import AsyncPostgresStore

T = TypeVar("T")


class IndexedColumn(NamedTuple):
    """One extra column, alongside the key and JSONB value, that rows can be
    looked up by -- and how to read its value off a T instance for writes."""

    name: str
    extract: Callable[[Any], Any]
    sql_type: str = "TEXT"
    unique: bool = False


def _identity(value: Any) -> Any:
    return value


class IndexedPostgresStore(AsyncPostgresStore[str, T], Generic[T]):
    """
    A Postgres table shaped like:
        <key_column> TEXT PRIMARY KEY, <extra_columns...>, <value_column> JSONB NOT NULL

    A real, fully-conformant AsyncKVStore[str, T] implementation (get/set
    inherited signatures, delete/close inherited unchanged) -- get/set are
    overridden entirely here (rather than via AsyncPostgresStore's
    _serialize_value/_deserialize_value hooks) since those assume a single
    value column; get/set here span every declared column instead. Being a
    genuine AsyncKVStore means any AsyncKVStore-typed consumer (e.g.
    UserIngredientInventoryStore) can be handed this, an InMemoryKVStore, or
    any other implementation interchangeably via DI.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        table_name: str = "store",
        key_column: str = "id",
        value_column: str = "data",
        extra_columns: Sequence[IndexedColumn] = (),
        serialize: Callable[[T], Any] = _identity,
        deserialize: Callable[[Dict[str, Any]], T] = _identity,
    ):
        super().__init__(
            connection_string=connection_string,
            table_name=table_name,
            key_column=key_column,
            value_column=value_column,
            create_table=True,
        )
        self.extra_columns = extra_columns
        self._serialize = serialize
        self._deserialize = deserialize

    async def _ensure_connection(self):
        if not self.connection_string:
            raise RuntimeError(
                f"No Postgres connection string configured for the '{self.table_name}' store. "
                f"Pass connection_string explicitly."
            )
        return await super()._ensure_connection()

    async def _create_table_if_not_exists(self) -> None:
        extra_columns_sql = "".join(f", {col.name} {col.sql_type}" for col in self.extra_columns)
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    {self.key_column} TEXT PRIMARY KEY{extra_columns_sql},
                    {self.value_column} JSONB NOT NULL
                )
            """)
            for col in self.extra_columns:
                unique_sql = "UNIQUE " if col.unique else ""
                await conn.execute(f"""
                    CREATE {unique_sql}INDEX IF NOT EXISTS {self.table_name}_{col.name}_idx
                    ON {self.table_name} ({col.name})
                """)

    async def _execute(self, query: str, *args: Any) -> str:
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _fetchrow(self, query: str, *args: Any):
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def _fetch(self, query: str, *args: Any):
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    def _all_column_names(self) -> List[str]:
        return [self.key_column, *(col.name for col in self.extra_columns), self.value_column]

    def _row_to_value(self, row) -> T:
        plain = {name: row[name] for name in self._all_column_names()}
        raw_blob = plain[self.value_column]
        plain[self.value_column] = json.loads(raw_blob) if isinstance(raw_blob, str) else raw_blob
        return self._deserialize(plain)

    async def set(self, key: str, value: T) -> None:
        """Insert `value` under `key` (deriving each extra column's value from it), or
        update every column if `key` already exists (i.e. always an upsert)."""
        data = json.dumps(self._serialize(value))
        extra_names = [col.name for col in self.extra_columns]
        extra_values = [col.extract(value) for col in self.extra_columns]
        columns = [self.key_column, *extra_names, self.value_column]
        values = [key, *extra_values, data]
        placeholders = [f"${i}" for i in range(1, len(values))] + [f"${len(values)}::jsonb"]
        update_clause = ", ".join(f"{name} = EXCLUDED.{name}" for name in (*extra_names, self.value_column))

        await self._execute(
            f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT ({self.key_column}) DO UPDATE SET {update_clause}
            """,
            *values,
        )

    async def get(self, key: str) -> Optional[T]:
        """Fetch and deserialize the value stored under `key`."""
        row = await self._fetchrow(
            f"SELECT {', '.join(self._all_column_names())} FROM {self.table_name} WHERE {self.key_column} = $1",
            key,
        )
        return self._row_to_value(row) if row is not None else None

    async def get_by_column(self, column: str, value: Any) -> Optional[T]:
        """Fetch and deserialize the first value where `column` equals `value`."""
        row = await self._fetchrow(
            f"SELECT {', '.join(self._all_column_names())} FROM {self.table_name} WHERE {column} = $1 LIMIT 1",
            value,
        )
        return self._row_to_value(row) if row is not None else None

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """List values, optionally filtered by exact-match extra-column values and ordered."""
        query = f"SELECT {', '.join(self._all_column_names())} FROM {self.table_name}"
        params: list = []

        for column, value in (filters or {}).items():
            params.append(value)
            query += (" WHERE " if len(params) == 1 else " AND ") + f"{column} = ${len(params)}"

        if order_by:
            query += f" ORDER BY {order_by} {'DESC' if descending else 'ASC'}"

        params.append(limit)
        query += f" LIMIT ${len(params)}"
        params.append(offset)
        query += f" OFFSET ${len(params)}"

        rows = await self._fetch(query, *params)
        return [self._row_to_value(row) for row in rows]
