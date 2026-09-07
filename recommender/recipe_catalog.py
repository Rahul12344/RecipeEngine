"""A minimal interface for "wherever candidate recipes come from".

The recommendation logic in this package only needs to be handed a
collection of `Recipe` objects to rank -- it should not care whether those
recipes come from an in-memory list, a Postgres-backed catalog, a file, or
anything else. `RecipeCatalog` is that seam: anything with a
`list_recipes()` method satisfies it structurally (it's a `Protocol`, so no
inheritance is required), which keeps this branch decoupled from whatever
persistent recipe store lands separately.
"""
from __future__ import annotations

from typing import Iterable, List, Protocol, runtime_checkable

from models.output_data_models.annotation_model_features import Recipe


@runtime_checkable
class RecipeCatalog(Protocol):
    def list_recipes(self) -> Iterable[Recipe]:
        """Return the current set of candidate recipes."""
        ...


class InMemoryRecipeCatalog:
    """A trivial `RecipeCatalog` backed by a plain in-memory list.

    Useful for tests and as a placeholder until a persistent (e.g.
    Postgres-backed) recipe catalog is wired in -- swapping one in later
    means constructing `RecipeRecommender`'s pipeline with a different
    `RecipeCatalog` implementation, nothing else changes.
    """

    def __init__(self, recipes: Iterable[Recipe] = ()):
        self._recipes: List[Recipe] = list(recipes)

    def list_recipes(self) -> Iterable[Recipe]:
        return list(self._recipes)

    def add_recipe(self, recipe: Recipe) -> None:
        self._recipes.append(recipe)
