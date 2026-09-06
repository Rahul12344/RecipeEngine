from di import provides
from models.output_data_models.annotation_model_features import RecipeAnnotation


@provides("recipe_annotation_store")
class RecipeAnnotationStore:
    def store(self, recipe_id: str, annotation: RecipeAnnotation) -> None:
        pass

    def get(self, recipe_id: str) -> RecipeAnnotation:
        pass

    def get_by_sort_key(self, sort_key: str) -> RecipeAnnotation:
        pass
