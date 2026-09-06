"""
Postgres-backed persistence for `RecipeAnnotation` (the further-annotated,
NER-enriched pipeline output). Built the same way as store/recipe_store.py:
on IndexedPostgresStore, which owns all connection/table/query plumbing, with
serialize/deserialize round-tripping into the real frozen dataclasses
(including the Diet/DietTag enums) rather than raw dicts.

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

import json
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


@provides("recipe_annotation_store")
class RecipeAnnotationStore(IndexedPostgresStore[RecipeAnnotation]):
    """Persists RecipeAnnotation objects to Postgres, keyed by recipe id."""

    extra_columns = (IndexedColumn("sort_key"),)

    def __init__(self, connection_string: Optional[str] = None, table_name: str = "recipe_annotations"):
        super().__init__(connection_string=connection_string, table_name=table_name, key_column="recipe_id")

    def _serialize_value(self, value: RecipeAnnotation) -> str:
        return json.dumps(annotation_to_dict(value))

    def _deserialize_value(self, json_str) -> RecipeAnnotation:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        return annotation_from_dict(data)

    async def store(self, recipe_id: str, annotation: RecipeAnnotation) -> None:
        await self._upsert(recipe_id, annotation, sort_key=annotation.recipe.name)

    async def get_by_sort_key(self, sort_key: str) -> Optional[RecipeAnnotation]:
        return await self._get_by_column("sort_key", sort_key)
