from data_pipeline.transformers.json_ld_recipe_transformer import JsonLdRecipeTransformer


class FoodNetworkTransformer(JsonLdRecipeTransformer):
    """
    Transformer for extracting recipe data from FoodNetwork.com HTML.

    FoodNetwork embeds a complete schema.org Recipe JSON-LD block with name,
    recipeIngredient, and recipeInstructions all present -- verified against
    an archive.org snapshot of a live FoodNetwork recipe page while building
    this pipeline (direct fetches from this sandbox are blocked by
    FoodNetwork's bot protection, but the archived HTML is byte-for-byte the
    same page). No CSS-selector fallback has been needed so far; this class
    relies entirely on the shared JsonLdRecipeTransformer.
    """
