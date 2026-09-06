"""
Postgres-backed persistence for `RecipeAnnotation` (the further-annotated,
NER-enriched pipeline output). Built the same way as store/recipe_store.py:
on top of AsyncPostgresStore's connection-pool/table plumbing, with
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
import logging
import os
from typing import Optional

from async_store.async_postgres_store import AsyncPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import (
    Diet,
    DietTag,
    Effort,
    RecipeAnnotation,
    RecipeMetadata,
)
from store.recipe_store import DATABASE_URL_ENV_VAR, recipe_from_dict, recipe_to_dict

logger = logging.getLogger(__name__)


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
class RecipeAnnotationStore(AsyncPostgresStore[str, RecipeAnnotation]):
    """Persists RecipeAnnotation objects to Postgres, keyed by recipe id."""

    def __init__(self, connection_string: Optional[str] = None, table_name: str = "recipe_annotations"):
        # See RecipeStore for why this defaults to None instead of being a
        # required arg: it keeps this class (registered via @provides)
        # zero-arg constructible for the DI container.
        super().__init__(
            connection_string=connection_string or os.environ.get(DATABASE_URL_ENV_VAR),
            table_name=table_name,
            key_column="recipe_id",
            value_column="data",
            create_table=True,
        )

    async def _ensure_connection(self):
        if not self.connection_string:
            raise RuntimeError(
                f"No Postgres connection string configured for RecipeAnnotationStore. "
                f"Set the {DATABASE_URL_ENV_VAR} environment variable or pass "
                f"connection_string explicitly."
            )
        return await super()._ensure_connection()

    async def _create_table_if_not_exists(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    {self.key_column} TEXT PRIMARY KEY,
                    sort_key TEXT,
                    {self.value_column} JSONB NOT NULL
                )
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_sort_key_idx
                ON {self.table_name} (sort_key)
            """)

    def _serialize_value(self, value: RecipeAnnotation) -> str:
        return json.dumps(annotation_to_dict(value))

    def _deserialize_value(self, json_str) -> RecipeAnnotation:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        return annotation_from_dict(data)

    async def store(self, recipe_id: str, annotation: RecipeAnnotation) -> None:
        pool = await self._ensure_connection()
        sort_key = annotation.recipe.name
        data = self._serialize_value(annotation)

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} ({self.key_column}, sort_key, {self.value_column})
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT ({self.key_column}) DO UPDATE SET
                    sort_key = EXCLUDED.sort_key,
                    {self.value_column} = EXCLUDED.{self.value_column}
                """,
                recipe_id,
                sort_key,
                data,
            )

    async def get_by_sort_key(self, sort_key: str) -> Optional[RecipeAnnotation]:
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {self.value_column} FROM {self.table_name} WHERE sort_key = $1 LIMIT 1",
                sort_key,
            )
        return self._deserialize_value(row[self.value_column]) if row is not None else None
