"""
Persistence for `RecipeAnnotation` (the further-annotated, NER-enriched
pipeline output).

This class has no Postgres-specific code at all: it's injected (via DI, see
store/postgres/recipe_annotation_backing_store.py) with a generic,
already-configured backing store and only translates between
RecipeAnnotation-shaped method calls (store/get/get_by_sort_key) and that
backing store's generic (upsert/get/get_by_column) API.

Note: RecipeAnnotation's own NER annotation models are still unimplemented
stubs elsewhere in the codebase (see models/neer_model), so nothing
currently produces real RecipeAnnotation data to persist here yet -- this
class exists so the store side is ready when that lands.

`get_by_sort_key` mirrors the (undocumented) original stub's signature.
Since the recipe id is a content hash and not something a person would sort
or browse by, this implementation treats the annotated recipe's *name*
(RecipeAnnotation.recipe.name) as the "sort key" -- the one obviously
human-meaningful secondary lookup available on this data today.
"""
from __future__ import annotations

from typing import Optional

from async_store.indexed_postgres_store import IndexedPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import RecipeAnnotation


@provides("recipe_annotation_store")
class RecipeAnnotationStore:
    """Persists RecipeAnnotation objects, keyed by recipe id. No SQL/Postgres details here."""

    def __init__(self, recipe_annotation_backing_store: IndexedPostgresStore):
        self._backing_store = recipe_annotation_backing_store

    async def store(self, recipe_id: str, annotation: RecipeAnnotation) -> None:
        await self._backing_store.upsert(recipe_id, annotation, sort_key=annotation.recipe.name)

    async def get(self, recipe_id: str) -> Optional[RecipeAnnotation]:
        return await self._backing_store.get(recipe_id)

    async def get_by_sort_key(self, sort_key: str) -> Optional[RecipeAnnotation]:
        return await self._backing_store.get_by_column("sort_key", sort_key)

    async def close(self) -> None:
        await self._backing_store.close()
