class RecipeRecommender:
    def __init__(
        self,
        recommender_pipeline: Pipeline
    ):
        self._recommender_pipeline = recommender_pipeline

    def __call__(
        self,
        user: User,
        recommendation_options: RecommendationOptions
    ) -> List[Recipe]:
        return recommender_pipeline(user, recommendation_options)