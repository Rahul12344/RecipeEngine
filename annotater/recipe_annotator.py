from __future__ import annotations

import logging

from di import provides
from models.output_data_models.annotation_model_features import RecipeAnnotation
from models.annotation_model import RecipeAnnotationModel

logger = logging.getLogger(__name__)

_MAX_RETRIES_BEFORE_MANUAL_ANNOTATION = 3


@provides("recipe_annotator")
class RecipeAnnotator:
    def __init__(
        self,
        extraction_pipeline: Pipeline,
        ingredient_extraction_model: IngredientExtractionModel,
        instruction_extraction_model: InstructionExtractionModel,
        recipe_categorization_model: RecipeCategorizationModel,
        recipe_effort_estimate_model: RecipeEffortEstimateModel
    ):
        self._recipe_annotation_pipeline = extraction_pipeline
        self._ingredient_extraction_model = ingredient_extraction_model
        self._instruction_extraction_model = instruction_extraction_model
        self._recipe_categorization_model = recipe_categorization_model
        self._recipe_effort_estimate_model = recipe_effort_estimate_model

    def __call__(self, recipe_text: str) -> RecipeAnnotation:
        return self._user_validation_loop(recipe_text)

    def _user_validation_loop(self, recipe_text: str) -> RecipeAnnotation:
        recipe_annotation = self._annotate_recipe(recipe_text)
        retries = 0
        while not self._user_validation(recipe_annotation):
            recipe_annotation = self._annotate_recipe(recipe_text)
            retries += 1
            if retries >= _MAX_RETRIES_BEFORE_MANUAL_ANNOTATION:
                logger.error("Max retries reached, please manually annotate the recipe")
                return self._manual_annotation(recipe_text)
        return recipe_annotation

    def _annotate_recipe(self, recipe_text: str) -> RecipeAnnotation:
        ingredients = self._ingredient_extraction_model(recipe_text)
        instructions = self._instruction_extraction_model(recipe_text)
        diet, diet_tags = self._recipe_categorization_model(recipe_text)
        effort = self._recipe_effort_estimate_model(recipe_text)
        # return RecipeAnnotation(
        #     ingredients=ingredients,
        #     instructions=instructions,
        #     diet=diet,
        #     diet_tags=diet_tags,
        #     effort=effort
        # )
        return self._recipe_annotation_pipeline(recipe_text)

    def _user_validation(self, annotation: RecipeAnnotation) -> bool:
        pass

    def _manual_annotation(self, recipe_text: str) -> RecipeAnnotation:
        pass
