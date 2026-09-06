"""
Postgres-backed persistence for parsed `Recipe` objects.

Built on IndexedPostgresStore (async_store/indexed_postgres_store.py), which
owns all connection/table/query plumbing; this class only supplies the
schema (extra_columns), the Recipe <-> JSON mapping, and its own query
methods -- it never touches a connection pool directly.

Query patterns for recipes beyond "by id/url/source" aren't known yet, so
the full nested Recipe (ingredients + instructions) lives in a single JSONB
column, plus a handful of real, indexable columns (source, url, name,
ingested_at) for the lookups that are obviously going to be needed. That's a
deliberate middle ground between a fully normalized multi-table schema
(premature) and dumping everything into an opaque blob (would make even
"recipes from source X" require a full scan).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from async_store.indexed_postgres_store import IndexedColumn, IndexedPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import (
    Recipe,
    RecipeIngredient,
    RecipeInstruction,
)


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
class RecipeStore(IndexedPostgresStore[Recipe]):
    """Persists parsed Recipe objects to Postgres, keyed by a hash of their source URL."""

    extra_columns = (
        IndexedColumn("source"),
        IndexedColumn("url", unique=True),
        IndexedColumn("name"),
        IndexedColumn("ingested_at", sql_type="TIMESTAMPTZ"),
    )

    def __init__(self, connection_string: Optional[str] = None, table_name: str = "recipes"):
        super().__init__(connection_string=connection_string, table_name=table_name, key_column="id")

    def _serialize_value(self, value: Recipe) -> str:
        return json.dumps(recipe_to_dict(value))

    def _deserialize_value(self, json_str) -> Recipe:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        return recipe_from_dict(data)

    async def save_recipe(self, recipe: Recipe, source: str, url: str) -> str:
        """
        Upsert a parsed Recipe, keyed by a stable hash of its source URL
        (re-scraping the same URL updates the existing row rather than
        creating a duplicate). Returns the recipe id.
        """
        recipe_id = recipe_id_for_url(url)
        await self._upsert(
            recipe_id,
            recipe,
            source=source,
            url=url,
            name=recipe.name,
            ingested_at=datetime.now(timezone.utc),
        )
        return recipe_id

    async def get_recipe(self, recipe_id: str) -> Optional[StoredRecipe]:
        """Fetch a stored recipe by id."""
        row = await self._fetchrow(
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

        rows = await self._fetch(base_query, *params)
        return [self._row_to_stored_recipe(row) for row in rows]

    def _row_to_stored_recipe(self, row) -> StoredRecipe:
        return StoredRecipe(
            id=row["id"],
            source=row["source"],
            url=row["url"],
            name=row["name"],
            ingested_at=row["ingested_at"],
            recipe=self._deserialize_value(row["data"]),
        )
