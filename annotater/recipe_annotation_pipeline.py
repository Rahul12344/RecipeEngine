from models.annotation_model_features import RecipeAnnotation
from annotater.recipe_annotator import RecipeAnnotator
from annotater.recipe_annotation_store import RecipeAnnotationStore
import hashlib

class RecipeAnnotationPipeline:
    def __init__(self, annotator: RecipeAnnotator, recipe_annotion_store: RecipeAnnotationStore):
        self._annotator = annotator
        self._recipe_annotation_store = recipe_annotion_store

    def __call__(self, recipe_text: str) -> None:
        annotation =self._annotator(recipe_text)
        recipe_id = self._generate_recipe_id(recipe_text)
        self._recipe_annotation_store.store(recipe_id, annotation)

    def _generate_recipe_id(self, recipe_text: list[str]) -> str:
        return hashlib.sha256(recipe_text.encode()).hexdigest()
