from data_pipeline.meta_info.source_metadata import Source, SourceMetadata

class FoodNetworkSourceMetadata(SourceMetadata):
    @property
    def name(self) -> str:
        return Source.FOOD_NETWORK.value

    @property
    def hostname(self) -> str:
        return "https://www.foodnetwork.com"

    @property
    def recipe_identifier(self) -> str:
        return "/recipes/"

    @property
    def recipe_link_pattern(self) -> set[str]:
        return {"/"}

