from di import provides
from models.output_data_models.annotation_model_features import RecipeAnnotation
from annotater.recipe_annotator import RecipeAnnotator
from store.recipe_annotation_store import RecipeAnnotationStore
import hashlib


@provides("recipe_annotation_pipeline")
class RecipeAnnotationPipeline:
    def __init__(self, recipe_annotator: RecipeAnnotator, recipe_annotation_store: RecipeAnnotationStore):
        self._annotator = recipe_annotator
        self._recipe_annotation_store = recipe_annotation_store

    def __call__(self, recipe_text: str) -> None:
        annotation =self._annotator(recipe_text)
        recipe_id = self._generate_recipe_id(recipe_text)
        self._recipe_annotation_store.store(recipe_id, annotation)

    def _generate_recipe_id(self, recipe_text: list[str]) -> str:
        return hashlib.sha256(recipe_text.encode()).hexdigest()
