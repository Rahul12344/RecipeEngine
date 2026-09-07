from __future__ import annotations

from typing import List

from di import provides
from models.output_data_models.annotation_model_features import Recipe
from pipelines.pipeline import Pipeline
from recommender.recommendation_options import RecommendationOptions
from recommender.user import User


@provides("recipe_recommender")
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
        # Pipeline steps are single-input/single-output (see
        # pipelines/pipeline.py), so the (user, options) pair is bundled
        # into one tuple for the pipeline to pass along its steps.
        return self._recommender_pipeline((user, recommendation_options))