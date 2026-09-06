from __future__ import annotations


class RecipeRecommendationModel:
    def __call__(
        self,
        user_features: UserFeatures,
    ) -> list[Recipe]:
        """Base model for generating recipe predictions."""
        pass

class CollaborativeFilteringModel(RecipeRecommendationModel):
    pass