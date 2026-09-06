"""
Shared plumbing for a Postgres-backed store of values of type T, identified
by a string key, with a handful of extra, independently-queryable columns
alongside a JSONB blob holding the value's full serialized structure.

Factors out what every concrete store in this codebase (RecipeStore,
RecipeAnnotationStore, UserIngredientInventoryStore) otherwise reimplements
on its own: reading the shared Postgres connection string from the
environment (raising a clear error if it's missing, rather than a confusing
asyncpg failure later), creating the table (+ indexes on the extra columns)
on first use, and running queries.

Concrete subclasses never see a connection pool, `asyncpg`, or
`_ensure_connection` at all -- not even for their own bespoke queries beyond
the generic upsert/get-by-column helpers here. They declare `extra_columns`,
implement `_serialize_value`/`_deserialize_value` (from AsyncPostgresStore)
for their own dataclass <-> JSON shape, and issue any additional queries
through `_execute`/`_fetchrow`/`_fetch`, passing SQL text and args only.
"""
from __future__ import annotations

import os
from typing import Any, Generic, NamedTuple, Optional, Sequence, TypeVar

from async_store.async_postgres_store import AsyncPostgresStore

T = TypeVar("T")

# Every store in this codebase shares one Postgres database (different
# tables), so this is one shared env var rather than one per store.
DATABASE_URL_ENV_VAR = "RECIPE_ENGINE_DATABASE_URL"


class IndexedColumn(NamedTuple):
    """One extra column, alongside the key and JSONB value, that rows can be looked up by."""

    name: str
    sql_type: str = "TEXT"
    unique: bool = False


class IndexedPostgresStore(AsyncPostgresStore[str, T], Generic[T]):
    """
    Base class for a Postgres table shaped like:
        <key_column> TEXT PRIMARY KEY, <extra_columns...>, <value_column> JSONB NOT NULL

    Subclasses set the `extra_columns` class attribute (empty by default) to
    declare any extra indexable columns beyond the key and JSONB value.
    """

    extra_columns: Sequence[IndexedColumn] = ()

    def __init__(
        self,
        connection_string: Optional[str] = None,
        table_name: str = "store",
        key_column: str = "id",
        value_column: str = "data",
    ):
        # `connection_string` defaults to None (rather than being required)
        # so subclasses stay zero-arg constructible for the DI container;
        # the real value is resolved from the environment here, or raised
        # as a clear error in `_ensure_connection` the first time a
        # connection is actually needed.
        super().__init__(
            connection_string=connection_string or os.environ.get(DATABASE_URL_ENV_VAR),
            table_name=table_name,
            key_column=key_column,
            value_column=value_column,
            create_table=True,
        )

    async def _ensure_connection(self):
        if not self.connection_string:
            raise RuntimeError(
                f"No Postgres connection string configured for {type(self).__name__}. "
                f"Set the {DATABASE_URL_ENV_VAR} environment variable or pass "
                f"connection_string explicitly."
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
        """Run a statement that doesn't return rows (INSERT/UPDATE/DELETE)."""
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _fetchrow(self, query: str, *args: Any):
        """Run a query and return its first row, or None."""
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def _fetch(self, query: str, *args: Any):
        """Run a query and return all matching rows."""
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def _upsert(self, key: str, value: T, **extra_values: Any) -> None:
        """
        Insert a row (key + extra_columns' values + serialized value), or
        update all of those columns if `key` already exists.

        `extra_values` must have exactly one keyword per declared
        `extra_columns` entry, by name.
        """
        data = self._serialize_value(value)
        extra_names = [col.name for col in self.extra_columns]
        columns = [self.key_column, *extra_names, self.value_column]
        values = [key, *(extra_values[name] for name in extra_names), data]
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

    async def _get_by_column(self, column: str, value: Any) -> Optional[T]:
        """Fetch and deserialize the first row where `column` equals `value`."""
        row = await self._fetchrow(
            f"SELECT {self.value_column} FROM {self.table_name} WHERE {column} = $1 LIMIT 1",
            value,
        )
        return self._deserialize_value(row[self.value_column]) if row is not None else None
