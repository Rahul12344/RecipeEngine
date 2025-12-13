class RecipeEffortEstimateModel:
    def __call__(
        self,
        features: RecipeEffortEstimateFeatures
    ) -> Effort:
        """Base class for recipe effort/difficulty prediction models."""
        pass
