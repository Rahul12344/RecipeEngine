from enum import Enum

class Source(Enum):
    ALL_RECIPES = "all_recipes"
    FOOD_DOT_COM = "food_dot_com"
    FOOD_NETWORK = "food_network"
    DELISH = "delish"

class SourceMetadata:
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