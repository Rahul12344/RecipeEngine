"""
Shared plumbing for a Postgres-backed store of values of type T, identified
by a string key, with a handful of extra, independently-queryable columns
alongside a JSONB blob holding the value's full serialized structure.

This is meant to be used directly (via composition), not subclassed: a
@provides-registered *function* builds a fully-configured instance (table
name, extra columns, serialize/deserialize) for a given entity type, and a
plain, backend-agnostic domain class (e.g. RecipeStore) is injected with
that instance and calls only its generic, non-SQL methods
(get/set/upsert/get_by_column/get_row/list_rows) -- no SQL, table names, or
JSONB casting ever appear in a domain class.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Generic, List, NamedTuple, Optional, Sequence, TypeVar

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


class Row(NamedTuple):
    """One stored record: its key, its extra column values by name, and its deserialized value."""

    key: str
    extra: Dict[str, Any]
    value: Any


class IndexedPostgresStore(AsyncPostgresStore[str, T], Generic[T]):
    """
    A Postgres table shaped like:
        <key_column> TEXT PRIMARY KEY, <extra_columns...>, <value_column> JSONB NOT NULL

    `serialize`/`deserialize` convert a value of type T to/from a JSON-able
    dict; if omitted, values are assumed to already be JSON-able as-is
    (matching AsyncPostgresStore's own default behavior).
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        table_name: str = "store",
        key_column: str = "id",
        value_column: str = "data",
        extra_columns: Sequence[IndexedColumn] = (),
        serialize: Optional[Callable[[T], Any]] = None,
        deserialize: Optional[Callable[[Any], T]] = None,
    ):
        super().__init__(
            connection_string=connection_string or os.environ.get(DATABASE_URL_ENV_VAR),
            table_name=table_name,
            key_column=key_column,
            value_column=value_column,
            create_table=True,
        )
        self.extra_columns = extra_columns
        self._serialize = serialize
        self._deserialize = deserialize

    def _serialize_value(self, value: T) -> str:
        return json.dumps(self._serialize(value) if self._serialize else value)

    def _deserialize_value(self, json_str) -> T:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        return self._deserialize(data) if self._deserialize else data

    async def _ensure_connection(self):
        if not self.connection_string:
            raise RuntimeError(
                f"No Postgres connection string configured for the '{self.table_name}' store. "
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

    def _row_to_generic(self, row) -> Row:
        extra = {col.name: row[col.name] for col in self.extra_columns}
        return Row(key=row[self.key_column], extra=extra, value=self._deserialize_value(row[self.value_column]))

    async def upsert(self, key: str, value: T, **extra_values: Any) -> None:
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

    async def get_by_column(self, column: str, value: Any) -> Optional[T]:
        """Fetch and deserialize the first row where `column` equals `value`."""
        row = await self._fetchrow(
            f"SELECT {self.value_column} FROM {self.table_name} WHERE {column} = $1 LIMIT 1",
            value,
        )
        return self._deserialize_value(row[self.value_column]) if row is not None else None

    async def get_row(self, key: str) -> Optional[Row]:
        """Fetch a row (extra column values + deserialized value) by its key."""
        columns = self._all_column_names()
        row = await self._fetchrow(
            f"SELECT {', '.join(columns)} FROM {self.table_name} WHERE {self.key_column} = $1",
            key,
        )
        return self._row_to_generic(row) if row is not None else None

    async def get_row_by_column(self, column: str, value: Any) -> Optional[Row]:
        """Fetch a row (extra column values + deserialized value) by any one column's value."""
        columns = self._all_column_names()
        row = await self._fetchrow(
            f"SELECT {', '.join(columns)} FROM {self.table_name} WHERE {column} = $1 LIMIT 1",
            value,
        )
        return self._row_to_generic(row) if row is not None else None

    async def list_rows(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Row]:
        """List rows, optionally filtered by exact-match extra-column values and ordered."""
        columns = self._all_column_names()
        query = f"SELECT {', '.join(columns)} FROM {self.table_name}"
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
        return [self._row_to_generic(row) for row in rows]

    def _all_column_names(self) -> List[str]:
        return [self.key_column, *(col.name for col in self.extra_columns), self.value_column]
