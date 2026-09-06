"""
Persistence for parsed `Recipe` objects.

This class has no Postgres-specific code at all: it's injected (via DI, see
store/postgres/recipe_backing_store.py) with a generic, already-configured
backing store and only translates between Recipe-shaped method calls
(save_recipe/get_recipe/get_by_url/list_recipes) and that backing store's
generic (upsert/get_row/get_row_by_column/list_rows) API.

Query patterns for recipes beyond "by id/url/source" aren't known yet, so
the full nested Recipe (ingredients + instructions) lives in a single JSONB
column, plus a handful of real, indexable columns for the lookups that are
obviously going to be needed. That's a deliberate middle ground between a
fully normalized multi-table schema (premature) and dumping everything into
an opaque blob (would make even "recipes from source X" require a full scan).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from async_store.indexed_postgres_store import IndexedPostgresStore, Row
from di import provides
from models.output_data_models.annotation_model_features import Recipe


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


@provides("recipe_store")
class RecipeStore:
    """Persists parsed Recipe objects, keyed by a hash of their source URL. No SQL/Postgres details here."""

    def __init__(self, recipe_backing_store: IndexedPostgresStore):
        self._backing_store = recipe_backing_store

    async def save_recipe(self, recipe: Recipe, source: str, url: str) -> str:
        """
        Upsert a parsed Recipe, keyed by a stable hash of its source URL
        (re-scraping the same URL updates the existing row rather than
        creating a duplicate). Returns the recipe id.
        """
        recipe_id = recipe_id_for_url(url)
        await self._backing_store.upsert(
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
        row = await self._backing_store.get_row(recipe_id)
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
        rows = await self._backing_store.list_rows(
            filters={"source": source} if source is not None else None,
            order_by="ingested_at",
            descending=True,
            limit=limit,
            offset=offset,
        )
        return [self._row_to_stored_recipe(row) for row in rows]

    async def close(self) -> None:
        await self._backing_store.close()

    def _row_to_stored_recipe(self, row: Row) -> StoredRecipe:
        return StoredRecipe(
            id=row.key,
            source=row.extra["source"],
            url=row.extra["url"],
            name=row.extra["name"],
            ingested_at=row.extra["ingested_at"],
            recipe=row.value,
        )
