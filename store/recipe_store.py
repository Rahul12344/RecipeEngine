"""
Postgres-backed persistence for parsed `Recipe` objects.

Built on top of AsyncPostgresStore (connection pooling + table bootstrap),
but doesn't use its generic key/value schema as-is: query patterns for
recipes beyond "by id/url/source" aren't known yet, so this keeps the full
nested Recipe (ingredients + instructions) in a single JSONB column, plus a
handful of real, indexable columns (source, url, name, ingested_at) for the
lookups that are obviously going to be needed. That's a deliberate middle
ground between a fully normalized multi-table schema (premature -- we don't
know the query patterns yet) and dumping everything into an opaque blob
(would make even "recipes from source X" require a full scan).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from async_store.async_postgres_store import AsyncPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import (
    Recipe,
    RecipeIngredient,
    RecipeInstruction,
)

logger = logging.getLogger(__name__)

# Postgres connection string is read from the environment (never hardcoded).
# See .env.example at the repo root.
DATABASE_URL_ENV_VAR = "RECIPE_ENGINE_DATABASE_URL"


def recipe_id_for_url(url: str) -> str:
    """
    Derive a stable recipe id from its source URL.

    Mirrors the sha256-of-text approach RecipeAnnotationPipeline already uses
    for annotation recipe ids (annotater/recipe_annotation_pipeline.py's
    `_generate_recipe_id`), just hashing the URL instead of the recipe text
    since the URL is stable across re-scrapes while raw HTML/text is not.
    """
    return hashlib.sha256(url.encode()).hexdigest()


@dataclass(frozen=True)
class StoredRecipe:
    """A persisted Recipe plus the indexable metadata columns stored alongside it."""

    id: str
    source: str
    url: str
    name: str
    ingested_at: datetime
    recipe: Recipe


def _ingredient_to_dict(ingredient: RecipeIngredient) -> dict:
    return {
        "name": ingredient.name,
        "quantity": ingredient.quantity,
        "unit": ingredient.unit,
        "process": ingredient.process,
    }


def _ingredient_from_dict(data: dict) -> RecipeIngredient:
    return RecipeIngredient(
        name=data["name"],
        quantity=data["quantity"],
        unit=data["unit"],
        process=data.get("process"),
    )


def _instruction_to_dict(instruction: RecipeInstruction) -> dict:
    return {
        "step": instruction.step,
        "description": instruction.description,
        "list_of_ingredients_for_step": [
            _ingredient_to_dict(i) for i in instruction.list_of_ingredients_for_step
        ],
    }


def _instruction_from_dict(data: dict) -> RecipeInstruction:
    return RecipeInstruction(
        step=data["step"],
        description=data["description"],
        list_of_ingredients_for_step=[
            _ingredient_from_dict(i) for i in data.get("list_of_ingredients_for_step", [])
        ],
    )


def recipe_to_dict(recipe: Recipe) -> dict:
    """Serialize a Recipe into a plain JSON-able dict (for the JSONB column)."""
    return {
        "name": recipe.name,
        "total_ingredients": [_ingredient_to_dict(i) for i in recipe.total_ingredients],
        "instructions": [_instruction_to_dict(i) for i in recipe.instructions],
    }


def recipe_from_dict(data: dict) -> Recipe:
    """Deserialize a Recipe (and its nested frozen dataclasses) back from a plain dict."""
    return Recipe(
        name=data["name"],
        total_ingredients=[_ingredient_from_dict(i) for i in data.get("total_ingredients", [])],
        instructions=[_instruction_from_dict(i) for i in data.get("instructions", [])],
    )


@provides("recipe_store")
class RecipeStore(AsyncPostgresStore[str, Recipe]):
    """
    Persists parsed Recipe objects to Postgres.

    Reuses AsyncPostgresStore for connection-pool management and lifecycle
    (`_ensure_connection`, `close`, async context manager support), but
    defines its own richer table schema and query methods rather than the
    base class's plain key/value contract.
    """

    def __init__(self, connection_string: Optional[str] = None, table_name: str = "recipes"):
        # `connection_string` defaults to None (rather than being required) so
        # this class stays zero-arg constructible for the DI container (it's
        # registered via @provides); the real value is resolved from
        # RECIPE_ENGINE_DATABASE_URL lazily, the first time a connection is
        # actually needed -- see `_ensure_connection`.
        super().__init__(
            connection_string=connection_string or os.environ.get(DATABASE_URL_ENV_VAR),
            table_name=table_name,
            key_column="id",
            value_column="data",
            create_table=True,
        )

    async def _ensure_connection(self):
        if not self.connection_string:
            raise RuntimeError(
                f"No Postgres connection string configured for RecipeStore. "
                f"Set the {DATABASE_URL_ENV_VAR} environment variable or pass "
                f"connection_string explicitly."
            )
        return await super()._ensure_connection()

    async def _create_table_if_not_exists(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    url TEXT,
                    name TEXT,
                    ingested_at TIMESTAMPTZ,
                    data JSONB NOT NULL
                )
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_source_idx
                ON {self.table_name} (source)
            """)
            await conn.execute(f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {self.table_name}_url_idx
                ON {self.table_name} (url)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_name_idx
                ON {self.table_name} (name)
            """)

    async def save_recipe(self, recipe: Recipe, source: str, url: str) -> str:
        """
        Upsert a parsed Recipe, keyed by a stable hash of its source URL
        (re-scraping the same URL updates the existing row rather than
        creating a duplicate). Returns the recipe id.
        """
        pool = await self._ensure_connection()
        recipe_id = recipe_id_for_url(url)
        ingested_at = datetime.now(timezone.utc)
        data = json.dumps(recipe_to_dict(recipe))

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (id, source, url, name, ingested_at, data)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    source = EXCLUDED.source,
                    url = EXCLUDED.url,
                    name = EXCLUDED.name,
                    ingested_at = EXCLUDED.ingested_at,
                    data = EXCLUDED.data
                """,
                recipe_id,
                source,
                url,
                recipe.name,
                ingested_at,
                data,
            )
        return recipe_id

    async def get_recipe(self, recipe_id: str) -> Optional[StoredRecipe]:
        """Fetch a stored recipe by id."""
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT id, source, url, name, ingested_at, data FROM {self.table_name} WHERE id = $1",
                recipe_id,
            )
        return self._row_to_stored_recipe(row) if row is not None else None

    async def get_by_url(self, url: str) -> Optional[StoredRecipe]:
        """Fetch a stored recipe by its original source URL."""
        return await self.get_recipe(recipe_id_for_url(url))

    async def list_recipes(
        self,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoredRecipe]:
        """List stored recipes, optionally filtered by source, newest-ingested first."""
        pool = await self._ensure_connection()
        base_query = f"SELECT id, source, url, name, ingested_at, data FROM {self.table_name}"
        params: list = []
        if source is not None:
            params.append(source)
            base_query += f" WHERE source = ${len(params)}"
        base_query += " ORDER BY ingested_at DESC"
        params.append(limit)
        base_query += f" LIMIT ${len(params)}"
        params.append(offset)
        base_query += f" OFFSET ${len(params)}"

        async with pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
        return [self._row_to_stored_recipe(row) for row in rows]

    def _row_to_stored_recipe(self, row) -> StoredRecipe:
        raw_data = row["data"]
        data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        return StoredRecipe(
            id=row["id"],
            source=row["source"],
            url=row["url"],
            name=row["name"],
            ingested_at=row["ingested_at"],
            recipe=recipe_from_dict(data),
        )
