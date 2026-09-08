"""A persisted Recipe plus the indexable metadata a store keeps alongside it.

Kept separate from annotation_model_features.py (pure recipe/annotation
content models): this is a storage-record shape, not a domain content
model, and both store/recipe_store.py and store/postgres/recipe_backing_store.py
need it -- living here (rather than inside one of those two files) means
neither has to import from the other.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from models.output_data_models.annotation_model_features import Recipe


@dataclass(frozen=True)
class StoredRecipe:
    """A persisted Recipe plus the indexable metadata columns stored alongside it."""

    id: str
    source: str
    url: str
    name: str
    ingested_at: datetime
    recipe: Recipe
