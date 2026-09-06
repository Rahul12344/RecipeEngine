"""
DI provider for the Postgres-backed store behind
store.recipe_annotation_store.RecipeAnnotationStore.

Builds a fully-configured IndexedPostgresStore for the `recipe_annotations`
table: the table name, extra indexable columns (sort_key), and the
RecipeAnnotation <-> JSON mapping (delegated to
RecipeAnnotation.to_dict/from_dict) all live here, kept separate from
RecipeAnnotationStore itself, which has no Postgres-specific code at all.
"""
from __future__ import annotations

from async_store.indexed_postgres_store import IndexedColumn, IndexedPostgresStore
from di import provides
from models.output_data_models.annotation_model_features import RecipeAnnotation


@provides("recipe_annotation_backing_store")
def build_recipe_annotation_backing_store() -> IndexedPostgresStore[RecipeAnnotation]:
    return IndexedPostgresStore(
        table_name="recipe_annotations",
        key_column="recipe_id",
        extra_columns=(IndexedColumn("sort_key"),),
        serialize=RecipeAnnotation.to_dict,
        deserialize=RecipeAnnotation.from_dict,
    )
