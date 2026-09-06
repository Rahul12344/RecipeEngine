"""
A tiny in-memory fake of the slice of the asyncpg API that
async_store.async_postgres_store.AsyncPostgresStore (and its subclasses,
RecipeStore / RecipeAnnotationStore) actually use: `create_pool`,
`pool.acquire()` as an async context manager yielding a connection with
`execute`/`fetchrow`/`fetch`.

Used by the store tests to exercise the real store code (SQL included)
without a live Postgres instance -- see store/tests/test_recipe_store.py
for why: no local Postgres is reachable in this environment.

This is intentionally narrow: it understands exactly the query shapes the
stores in this repo issue (CREATE TABLE/INDEX, single-row upsert INSERT ...
ON CONFLICT, SELECT ... WHERE <col> = $1, and a filtered/paginated SELECT
... ORDER BY ... LIMIT ... OFFSET ...), not general SQL.
"""
from __future__ import annotations

import re
from typing import Any, Optional


class FakeConnection:
    def __init__(self, pool: "FakeAsyncpgPool"):
        self._pool = pool

    async def execute(self, query: str, *args: Any) -> str:
        normalized = " ".join(query.split())
        upper = normalized.upper()
        if upper.startswith("CREATE TABLE") or upper.startswith("CREATE INDEX") or upper.startswith("CREATE UNIQUE INDEX"):
            return "CREATE"
        if upper.startswith("INSERT INTO"):
            return self._pool.handle_insert(normalized, args)
        if upper.startswith("DELETE FROM"):
            return self._pool.handle_delete(normalized, args)
        raise NotImplementedError(f"FakeConnection.execute doesn't support: {normalized}")

    async def fetchrow(self, query: str, *args: Any) -> Optional[dict]:
        normalized = " ".join(query.split())
        return self._pool.handle_fetchrow(normalized, args)

    async def fetch(self, query: str, *args: Any) -> list[dict]:
        normalized = " ".join(query.split())
        return self._pool.handle_fetch(normalized, args)


class _AcquireContext:
    def __init__(self, pool: "FakeAsyncpgPool"):
        self._pool = pool

    async def __aenter__(self) -> FakeConnection:
        return FakeConnection(self._pool)

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeAsyncpgPool:
    """In-memory stand-in for an asyncpg.Pool, keyed by table name -> {pk: row dict}."""

    def __init__(self):
        self.tables: dict[str, dict[Any, dict]] = {}

    def acquire(self) -> _AcquireContext:
        return _AcquireContext(self)

    async def close(self) -> None:
        pass

    # -- query handling -------------------------------------------------

    def handle_insert(self, query: str, args: tuple) -> str:
        table = re.search(r"INSERT INTO\s+(\S+)", query, re.IGNORECASE).group(1)
        columns = [
            c.strip()
            for c in re.search(r"\(([^)]+)\)", query).group(1).split(",")
        ]
        row = dict(zip(columns, args))
        pk_column = columns[0]  # every INSERT in this codebase lists the primary key first
        table_rows = self.tables.setdefault(table, {})
        table_rows[row[pk_column]] = row
        return "INSERT 0 1"

    def handle_delete(self, query: str, args: tuple) -> str:
        table = re.search(r"DELETE FROM\s+(\S+)", query, re.IGNORECASE).group(1)
        match = re.search(r"WHERE\s+(\w+)\s*=\s*\$1", query, re.IGNORECASE)
        table_rows = self.tables.get(table, {})
        if not match:
            return "DELETE 0"
        column, value = match.group(1), args[0]
        to_delete = [pk for pk, row in table_rows.items() if row.get(column) == value]
        for pk in to_delete:
            del table_rows[pk]
        return f"DELETE {len(to_delete)}"

    def handle_fetchrow(self, query: str, args: tuple) -> Optional[dict]:
        table = re.search(r"FROM\s+(\S+)", query, re.IGNORECASE).group(1)
        table_rows = self.tables.get(table, {})
        match = re.search(r"WHERE\s+(\w+)\s*=\s*\$1", query, re.IGNORECASE)
        if not match:
            return None
        column, value = match.group(1), args[0]
        for row in table_rows.values():
            if row.get(column) == value:
                return dict(row)
        return None

    def handle_fetch(self, query: str, args: tuple) -> list[dict]:
        table = re.search(r"FROM\s+(\S+)", query, re.IGNORECASE).group(1)
        rows = list(self.tables.get(table, {}).values())
        remaining_args = list(args)

        if re.search(r"WHERE\s+source\s*=\s*\$1", query, re.IGNORECASE):
            source = remaining_args.pop(0)
            rows = [r for r in rows if r.get("source") == source]

        if re.search(r"ORDER BY\s+ingested_at\s+DESC", query, re.IGNORECASE):
            rows.sort(key=lambda r: r.get("ingested_at"), reverse=True)

        if re.search(r"LIMIT\s+\$\d+\s+OFFSET\s+\$\d+", query, re.IGNORECASE):
            limit, offset = remaining_args[-2], remaining_args[-1]
            rows = rows[offset:offset + limit]

        return [dict(r) for r in rows]
