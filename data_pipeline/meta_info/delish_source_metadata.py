from data_pipeline.meta_info.source_metadata import Source, SourceMetadata

class DelishSourceMetadata(SourceMetadata):
    @property
    def name(self) -> str:
        return Source.DELISH.value

    @property
    def hostname(self) -> str:
        return "https://www.delish.com"

    @property
    def recipe_identifier(self) -> str:
        return "/cooking/recipe-ideas/"

    @property
    def recipe_link_pattern(self) -> set[str]:
        return {"/"}

