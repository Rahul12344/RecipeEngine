"""Inventory-based recipe ranking.

The core idea: given a user's on-hand ingredients and a pool of candidate
recipes, score each recipe by what fraction of its ingredients the user
already has, rank recipes with the highest coverage first, and break ties
by whichever recipe is missing the fewest ingredients. This is a simple,
deterministic, rule-based approach on purpose -- see
`models/recommendation_models/recipe_recommendation_model.py` for the
(currently unused) interface reserved for future model-based approaches.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from models.features.user_ingredient_inventory import UserIngredientInventory
from models.output_data_models.annotation_model_features import Recipe
from recommender.ingredient_matching import ingredients_match
from recommender.recipe_catalog import RecipeCatalog
from recommender.recommendation_options import RecommendationOptions
from recommender.user import User

# The single input `InventoryMatchStep` expects: a `User` (carrying their
# resolved inventory) and the `RecommendationOptions` for this request.
RecommendationRequest = Tuple[User, RecommendationOptions]


@dataclass(frozen=True)
class RecipeMatchScore:
    """How well one recipe is covered by a user's inventory."""

    recipe: Recipe
    matched_count: int
    total_count: int
    missing_ingredients: List[str]

    @property
    def match_ratio(self) -> float:
        """Fraction of the recipe's ingredients the inventory covers, in
        [0.0, 1.0]. A recipe with no ingredients is trivially fully
        makeable, so it scores 1.0 rather than dividing by zero."""
        if self.total_count == 0:
            return 1.0
        return self.matched_count / self.total_count

    @property
    def missing_count(self) -> int:
        return len(self.missing_ingredients)


def score_recipe(recipe: Recipe, inventory_item_names: Iterable[str]) -> RecipeMatchScore:
    """Score a single recipe against a flat list of on-hand ingredient names."""
    have_names = list(inventory_item_names)
    missing_ingredients: List[str] = []
    matched_count = 0

    for ingredient in recipe.total_ingredients:
        if any(ingredients_match(have, ingredient.name) for have in have_names):
            matched_count += 1
        else:
            missing_ingredients.append(ingredient.name)

    return RecipeMatchScore(
        recipe=recipe,
        matched_count=matched_count,
        total_count=len(recipe.total_ingredients),
        missing_ingredients=missing_ingredients,
    )


def rank_recipes_by_inventory(
    recipes: Iterable[Recipe],
    inventory: UserIngredientInventory,
) -> List[RecipeMatchScore]:
    """Score and rank every recipe by inventory coverage.

    Order: highest match ratio first; ties broken by fewest missing
    ingredients; remaining ties broken by recipe name for determinism.
    """
    inventory_item_names = [item.name for item in inventory.items]
    scores = [score_recipe(recipe, inventory_item_names) for recipe in recipes]
    scores.sort(key=lambda score: (-score.match_ratio, score.missing_count, score.recipe.name))
    return scores


class InventoryMatchStep:
    """A `Pipeline`-compatible step that ranks a `RecipeCatalog`'s recipes
    by how completely a user's ingredient inventory covers each one.

    Takes a `RecommendationRequest` (a `(User, RecommendationOptions)`
    tuple) as produced by `RecipeRecommender`, and returns a `list[Recipe]`
    in ranked order, honoring `RecommendationOptions.min_match_ratio` and
    `RecommendationOptions.limit`.
    """

    def __init__(self, recipe_catalog: RecipeCatalog):
        self._recipe_catalog = recipe_catalog

    def __call__(self, step_input: RecommendationRequest) -> List[Recipe]:
        user, options = step_input
        scores = rank_recipes_by_inventory(self._recipe_catalog.list_recipes(), user.get_inventory())

        if options.min_match_ratio > 0.0:
            scores = [score for score in scores if score.match_ratio >= options.min_match_ratio]

        if options.limit is not None:
            scores = scores[: options.limit]

        return [score.recipe for score in scores]
