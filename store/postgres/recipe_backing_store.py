"""
DI provider for the Postgres-backed store behind store.recipe_store.RecipeStore.

Builds a fully-configured IndexedPostgresStore for the `recipes` table: the
table name, extra indexable columns (source, url, name, ingested_at), and
the Recipe <-> JSON mapping (delegated to Recipe.to_dict/from_dict) all live
here, kept separate from RecipeStore itself, which has no Postgres-specific
code at all.
"""
from __future__ import annotations

from async_store.indexed_postgres_store import IndexedColumn, IndexedPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import Recipe


@provides("recipe_backing_store")
def build_recipe_backing_store() -> IndexedPostgresStore[Recipe]:
    return IndexedPostgresStore(
        table_name="recipes",
        key_column="id",
        extra_columns=(
            IndexedColumn("source"),
            IndexedColumn("url", unique=True),
            IndexedColumn("name"),
            IndexedColumn("ingested_at", sql_type="TIMESTAMPTZ"),
        ),
        serialize=Recipe.to_dict,
        deserialize=Recipe.from_dict,
    )
