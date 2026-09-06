"""
DI provider for the Postgres-backed store behind store.recipe_store.RecipeStore.

Builds a fully-configured IndexedPostgresStore for the `recipes` table: the
table name, extra indexable columns (source, url, name, ingested_at) and how
to read each off a StoredRecipe, and the StoredRecipe <-> row mapping all
live here, kept separate from RecipeStore itself, which has no
Postgres-specific code at all.
"""
from __future__ import annotations

from async_store.indexed_postgres_store import IndexedColumn, IndexedPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import Recipe
from store.recipe_store import StoredRecipe


def _stored_recipe_from_row(row: dict) -> StoredRecipe:
    return StoredRecipe(
        id=row["id"],
        source=row["source"],
        url=row["url"],
        name=row["name"],
        ingested_at=row["ingested_at"],
        recipe=Recipe.from_dict(row["data"]),
    )


@provides("recipe_backing_store")
def build_recipe_backing_store() -> IndexedPostgresStore[StoredRecipe]:
    return IndexedPostgresStore(
        table_name="recipes",
        key_column="id",
        extra_columns=(
            IndexedColumn("source", extract=lambda stored: stored.source),
            IndexedColumn("url", extract=lambda stored: stored.url, unique=True),
            IndexedColumn("name", extract=lambda stored: stored.name),
            IndexedColumn("ingested_at", extract=lambda stored: stored.ingested_at, sql_type="TIMESTAMPTZ"),
        ),
        serialize=lambda stored: stored.recipe.to_dict(),
        deserialize=_stored_recipe_from_row,
    )
