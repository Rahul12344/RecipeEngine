from enum import Enum
from annotater.recipe_annotation_pipeline import RecipeAnnotationPipeline

class Source(Enum):
    SOURCE_ALL_RECIPES = "all_recipes"

class RecipeRetriever:
    def __init__(self, recipe_annotation_pipeline: RecipeAnnotationPipeline, recipe_source_retrievers: dict[Source, RecipeSourceRetriever]):
        self._recipe_annotation_pipeline = recipe_annotation_pipeline
        self._recipe_source_retrievers = recipe_source_retrievers

    def save_recipe_from_url(self, recipe_url: str, source: Source) -> None:
        if not (
            recipe_source_retriever := self._recipe_source_retrievers.get(source)
        ):
            raise ValueError(f"No recipe source retriever found for source: {source}")
        recipes = recipe_source_retriever.get_recipe_from_url(recipe_url)
        for recipe in recipes:
            self._recipe_annotation_pipeline(self._get_recipe_text_from_recipe_dict(recipe))

    def get_and_save_recipes_from_source(self, source: Source) -> None:
        if not (
            recipe_source_retriever := self._recipe_source_retrievers.get(source)
        ):
            raise ValueError(f"No recipe source retriever found for source: {source}")

        recipes = recipe_source_retriever.get_recipes()
        for recipe in recipes:
            self._recipe_annotation_pipeline(self._get_recipe_text_from_recipe_dict(recipe))

    def _get_recipe_text_from_recipe_dict(self, recipe_dict: dict) -> str:
        return "\n\n".join([f"{k.upper()}\n{k}: {v}" for k, v in recipe_dict.items()])


