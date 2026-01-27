from data_pipeline.meta_info.source_metadata import Source, SourceMetadata

class FoodDotComSourceMetadata(SourceMetadata):
    @property
    def name(self) -> str:
        return Source.FOOD_DOT_COM.value

    @property
    def hostname(self) -> str:
        return "https://www.food.com"

    @property
    def recipe_identifier(self) -> str:
        return "/recipe/"

    @property
    def recipe_link_pattern(self) -> set[str]:
        return {"/recipe/", "/ideas/"}

