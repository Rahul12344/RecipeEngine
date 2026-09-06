"""Maps each supported Source to its RecipeTransformerInterface implementation."""
from data_pipeline.meta_info.source_metadata import Source
from data_pipeline.transformers.allrecipes_transformer import AllRecipesTransformer
from data_pipeline.transformers.delish_transformer import DelishTransformer
from data_pipeline.transformers.food_dot_com_transformer import FoodDotComTransformer
from data_pipeline.transformers.food_network_transformer import FoodNetworkTransformer
from data_pipeline.transformers.recipe_transformer_interface import RecipeTransformerInterface


def default_transformers() -> dict[str, RecipeTransformerInterface]:
    """Return a fresh mapping of Source.value -> transformer instance for all supported sources."""
    return {
        Source.ALL_RECIPES.value: AllRecipesTransformer(),
        Source.DELISH.value: DelishTransformer(),
        Source.FOOD_NETWORK.value: FoodNetworkTransformer(),
        Source.FOOD_DOT_COM.value: FoodDotComTransformer(),
    }
