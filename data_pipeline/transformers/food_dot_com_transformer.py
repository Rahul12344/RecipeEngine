from data_pipeline.transformers.json_ld_recipe_transformer import JsonLdRecipeTransformer


class FoodDotComTransformer(JsonLdRecipeTransformer):
    """
    Transformer for extracting recipe data from Food.com HTML.

    Food.com embeds a complete schema.org Recipe JSON-LD block with name,
    recipeIngredient, and recipeInstructions all present -- verified against
    a live Food.com recipe page while building this pipeline. No
    CSS-selector fallback has been needed so far; this class relies
    entirely on the shared JsonLdRecipeTransformer.
    """
