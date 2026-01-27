import json
from typing import TypeVar, Optional
import asyncpg
from async_store.async_kv_store import AsyncKVStore

K = TypeVar('K')
V = TypeVar('V')

class AsyncPostgresStore(AsyncKVStore[K, V]):
    """
    PostgreSQL implementation of AsyncKVStore using asyncpg.
    Stores key-value pairs in a PostgreSQL table with JSON serialization.
    """

    def __init__(
        self,
        connection_string: str,
        table_name: str = "kv_store",
        key_column: str = "key",
        value_column: str = "value",
        create_table: bool = True
    ):
        """
        Initialize the PostgreSQL store.

        Args:
            connection_string: PostgreSQL connection string
            table_name: Name of the table to store key-value pairs
            key_column: Name of the column for keys
            value_column: Name of the column for values
            create_table: Whether to create the table if it doesn't exist
        """
        self.connection_string = connection_string
        self.table_name = table_name
        self.key_column = key_column
        self.value_column = value_column
        self.create_table = create_table
        self._pool: Optional[asyncpg.Pool] = None

    async def _ensure_connection(self) -> asyncpg.Pool:
        """Ensure the connection pool is initialized."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.connection_string)
            if self.create_table:
                await self._create_table_if_not_exists()
        return self._pool

    async def _create_table_if_not_exists(self) -> None:
        """Create the key-value table if it doesn't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    {self.key_column} TEXT PRIMARY KEY,
                    {self.value_column} JSONB NOT NULL
                )
            """)

    def _serialize_key(self, key: K) -> str:
        """Serialize key to string for storage."""
        if isinstance(key, str):
            return key
        return json.dumps(key)

    def _serialize_value(self, value: V) -> str:
        """Serialize value to JSON string for storage."""
        return json.dumps(value, default=str)

    def _deserialize_value(self, json_str: str) -> V:
        """Deserialize JSON string back to value."""
        return json.loads(json_str)

    async def get(self, key: K) -> Optional[V]:
        """Retrieve a value by key."""
        pool = await self._ensure_connection()
        serialized_key = self._serialize_key(key)

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {self.value_column} FROM {self.table_name} WHERE {self.key_column} = $1",
                serialized_key
            )

            if row is None:
                return None

            return self._deserialize_value(row[self.value_column])

    async def set(self, key: K, value: V) -> None:
        """Store a value with the given key."""
        pool = await self._ensure_connection()
        serialized_key = self._serialize_key(key)
        serialized_value = self._serialize_value(value)

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} ({self.key_column}, {self.value_column})
                VALUES ($1, $2::jsonb)
                ON CONFLICT ({self.key_column})
                DO UPDATE SET {self.value_column} = $2::jsonb
                """,
                serialized_key,
                serialized_value
            )

    async def delete(self, key: K) -> bool:
        """Delete a key-value pair."""
        pool = await self._ensure_connection()
        serialized_key = self._serialize_key(key)

        async with pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE {self.key_column} = $1",
                serialized_key
            )
            # asyncpg execute returns a string like "DELETE 1" or "DELETE 0"
            # Extract the number and check if it's greater than 0
            deleted_count = int(result.split()[-1])
            return deleted_count > 0

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

