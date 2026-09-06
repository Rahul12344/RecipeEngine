from data_pipeline.transformers.json_ld_recipe_transformer import JsonLdRecipeTransformer


class DelishTransformer(JsonLdRecipeTransformer):
    """
    Transformer for extracting recipe data from Delish.com HTML.

    Delish embeds a complete schema.org Recipe JSON-LD block
    (`<script id="json-ld" type="application/ld+json">`) with name,
    recipeIngredient, and recipeInstructions all present -- verified against
    a live Delish recipe page while building this pipeline. No CSS-selector
    fallback has been needed so far; this class relies entirely on the
    shared JsonLdRecipeTransformer.
    """
