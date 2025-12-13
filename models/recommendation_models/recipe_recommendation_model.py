class CollaborativeFilteringModel(RecipeRecommendationModel):
    pass

class RecipeRecommendationModel:
    def __call__(
        self,
        user_features: UserFeatures,
    ) -> list[Recipe]:
        """Base model for generating recipe predictions."""
        pass