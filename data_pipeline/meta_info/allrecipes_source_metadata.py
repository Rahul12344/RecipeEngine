from data_pipeline.meta_info.source_metadata import Source, SourceMetadata

class AllRecipesSourceMetadata(SourceMetadata):
    @property
    def name(self) -> str:
        return Source.ALL_RECIPES.value

    @property
    def hostname(self) -> str:
        return "https://www.allrecipes.com"

    @property
    def recipe_identifier(self) -> str:
        return "/recipe/"

    @property
    def recipe_link_pattern(self) -> set[str]:
        return {"/recipe/", "/recipes/"}

