from __future__ import annotations

from di import provides


@provides("recipe_categorization_model")
class RecipeCategorizationModel:
    def __call__(
        self,
        features: RecipeCategorizationFeatures
    ) -> list[Diet, list[DietTag]]:
        """Base class for tagging the recipe with the diet (vegan, vegetarian, non-veg, pescatarian)
        and diet type.
        """
