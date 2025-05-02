from models.annotation_model_features import RecipeAnnotation
from models.annotation_model import RecipeAnnotationModel
from logging import logger

_MAX_RETRIES_BEFORE_MANUAL_ANNOTATION = 3

class RecipeAnnotator:
    def __init__(self, annotation_model: RecipeAnnotationModel):
        self._annotation_model = annotation_model

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
        return self._annotation_model(recipe_text)

    def _user_validation(self, annotation: RecipeAnnotation) -> bool:
        pass

    def _manual_annotation(self, recipe_text: str) -> RecipeAnnotation:
        pass
