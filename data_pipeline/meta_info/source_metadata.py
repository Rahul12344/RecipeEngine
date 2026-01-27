from enum import Enum

class Source(Enum):
    ALL_RECIPES = "all_recipes"
    FOOD_DOT_COM = "food_dot_com"
    FOOD_NETWORK = "food_network"
    DELISH = "delish"

class SourceMetadata:
    """
    Base class that controls the meta info for a recipe source, including name, hostname,
    link identifiers, and HTML extraction rules.
    """
    @property
    def name(self) -> str:
        raise NotImplementedError("Subclasses must implement name property")

    @property
    def hostname(self) -> str:
        raise NotImplementedError("Subclasses must implement hostname property")

    @property
    def recipe_identifier(self) -> str:
        raise NotImplementedError("Subclasses must implement recipe_identifier property")

    @property
    def recipe_link_pattern(self) -> set[str]:
        raise NotImplementedError("Subclasses must implement recipe_identifier property")