"""
Postgres-backed persistence for `RecipeAnnotation` (the further-annotated,
NER-enriched pipeline output).

`recipe_annotation_backing_store` (a DI provider *function* -- see
di/provides.py) builds a fully-configured IndexedPostgresStore for the
`recipe_annotations` table. RecipeAnnotationStore itself is a plain class
with no SQL, table names, or JSONB in it -- it's injected with that backing
store and only translates between RecipeAnnotation-shaped method calls
(store/get/get_by_sort_key) and the backing store's generic
(upsert/get/get_by_column) API.

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

from async_store.indexed_postgres_store import IndexedColumn, IndexedPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import (
    Diet,
    DietTag,
    Effort,
    RecipeAnnotation,
    RecipeMetadata,
)
from store.recipe_store import recipe_from_dict, recipe_to_dict


def _effort_to_dict(effort: Effort) -> dict:
    return {
        "cook_time": effort.cook_time,
        "prep_time": effort.prep_time,
        "difficulty": effort.difficulty,
        "cost": effort.cost,
    }


def _effort_from_dict(data: dict) -> Effort:
    return Effort(
        cook_time=data["cook_time"],
        prep_time=data["prep_time"],
        difficulty=data["difficulty"],
        cost=data["cost"],
    )


def _metadata_to_dict(metadata: RecipeMetadata) -> dict:
    return {
        "diet": metadata.diet.value,
        "group": metadata.group,
        "effort": _effort_to_dict(metadata.effort),
        "diet_tags": [tag.value for tag in metadata.diet_tags],
    }


def _metadata_from_dict(data: dict) -> RecipeMetadata:
    return RecipeMetadata(
        diet=Diet(data["diet"]),
        group=data["group"],
        effort=_effort_from_dict(data["effort"]),
        diet_tags=[DietTag(tag) for tag in data.get("diet_tags", [])],
    )


def annotation_to_dict(annotation: RecipeAnnotation) -> dict:
    return {
        "recipe": recipe_to_dict(annotation.recipe),
        "recipe_metadata": _metadata_to_dict(annotation.recipe_metadata),
    }


def annotation_from_dict(data: dict) -> RecipeAnnotation:
    return RecipeAnnotation(
        recipe=recipe_from_dict(data["recipe"]),
        recipe_metadata=_metadata_from_dict(data["recipe_metadata"]),
    )


@provides("recipe_annotation_backing_store")
def build_recipe_annotation_backing_store() -> IndexedPostgresStore[RecipeAnnotation]:
    return IndexedPostgresStore(
        table_name="recipe_annotations",
        key_column="recipe_id",
        extra_columns=(IndexedColumn("sort_key"),),
        serialize=annotation_to_dict,
        deserialize=annotation_from_dict,
    )


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
