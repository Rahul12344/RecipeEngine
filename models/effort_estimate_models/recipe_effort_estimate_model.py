from __future__ import annotations

from di import provides


@provides("recipe_effort_estimate_model")
class RecipeEffortEstimateModel:
    def __call__(
        self,
        features: RecipeEffortEstimateFeatures
    ) -> Effort:
        """Base class for recipe effort/difficulty prediction models."""
        pass
