"""
Offline, deterministic unit tests for the recipe transformers, run against
saved HTML fixtures (data_pipeline/transformers/tests/fixtures/) rather than
live network calls.

The JSON-LD fixtures (allrecipes_recipe.html, delish_recipe.html,
foodnetwork_recipe.html, foodcom_recipe.html) embed the real, trimmed
schema.org Recipe JSON-LD captured by hand from a live or archived example
page of each site while building this pipeline -- see the docstrings in
data_pipeline/transformers/*_transformer.py for how each was obtained.
allrecipes_recipe_no_jsonld.html additionally exercises AllRecipesTransformer's
CSS-selector fallback path, using that same page's real (non-JSON-LD) markup.
"""
import os
import unittest

from data_pipeline.transformers.allrecipes_transformer import AllRecipesTransformer
from data_pipeline.transformers.delish_transformer import DelishTransformer
from data_pipeline.transformers.food_dot_com_transformer import FoodDotComTransformer
from data_pipeline.transformers.food_network_transformer import FoodNetworkTransformer
from data_pipeline.transformers.json_ld_recipe import find_recipe_json_ld, recipe_from_json_ld
from data_pipeline.transformers.transformer_registry import default_transformers
from data_pipeline.meta_info.source_metadata import Source

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return f.read()


class JsonLdRecipeExtractionTest(unittest.TestCase):
    """Tests for the shared JSON-LD parsing helpers directly."""

    def test_type_as_list_is_recognized_as_recipe(self):
        # AllRecipes' JSON-LD uses @type: ["Recipe", "NewsArticle"].
        html = _load_fixture("allrecipes_recipe.html")
        item = find_recipe_json_ld(html)
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "Easy Meatloaf")

    def test_no_json_ld_returns_none(self):
        html = _load_fixture("non_recipe_page.html")
        self.assertIsNone(find_recipe_json_ld(html))

    def test_no_json_ld_at_all_returns_none(self):
        self.assertIsNone(find_recipe_json_ld("<html><body><h1>Nothing here</h1></body></html>"))

    def test_recipe_from_json_ld_requires_name(self):
        self.assertIsNone(recipe_from_json_ld({"@type": "Recipe", "recipeIngredient": ["egg"]}))

    def test_recipe_from_json_ld_flattens_howto_sections(self):
        item = {
            "@type": "Recipe",
            "name": "Sectioned Recipe",
            "recipeIngredient": ["a", "b"],
            "recipeInstructions": [
                {
                    "@type": "HowToSection",
                    "name": "Prep",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": "Do step one."},
                        {"@type": "HowToStep", "text": "Do step two."},
                    ],
                }
            ],
        }
        recipe = recipe_from_json_ld(item)
        self.assertEqual([i.description for i in recipe.instructions], ["Do step one.", "Do step two."])

    def test_recipe_from_json_ld_handles_plain_string_instructions(self):
        item = {
            "@type": "Recipe",
            "name": "Plain String Steps",
            "recipeIngredient": ["a"],
            "recipeInstructions": "Step one.\nStep two.",
        }
        recipe = recipe_from_json_ld(item)
        self.assertEqual([i.description for i in recipe.instructions], ["Step one.", "Step two."])


class PerSiteTransformerTest(unittest.TestCase):
    """
    Runs the same assertions against each of the 4 site transformers via
    their real fixture pages, to confirm the shared JSON-LD path works
    end-to-end for every supported source.
    """

    CASES = [
        ("allrecipes_recipe.html", AllRecipesTransformer, "Easy Meatloaf", 9, 5),
        ("delish_recipe.html", DelishTransformer, "Instant Pot Pot Roast & Potatoes", 15, 4),
        ("foodnetwork_recipe.html", FoodNetworkTransformer, "Perfect Roast Chicken", 11, 3),
        ("foodcom_recipe.html", FoodDotComTransformer, "Toll House Butterscotch Chip Cookies", 9, 7),
    ]

    def test_is_recipe_page_true_for_each_site(self):
        for fixture, transformer_cls, *_ in self.CASES:
            with self.subTest(fixture=fixture):
                html = _load_fixture(fixture)
                self.assertTrue(transformer_cls().is_recipe_page(html))

    def test_transform_extracts_expected_fields_for_each_site(self):
        for fixture, transformer_cls, expected_name, num_ingredients, num_instructions in self.CASES:
            with self.subTest(fixture=fixture):
                html = _load_fixture(fixture)
                recipe = transformer_cls().transform(html, url=f"https://example.com/{fixture}")
                self.assertIsNotNone(recipe)
                self.assertEqual(recipe.name, expected_name)
                self.assertEqual(len(recipe.total_ingredients), num_ingredients)
                self.assertEqual(len(recipe.instructions), num_instructions)
                # step numbers should be 1..N in order
                self.assertEqual(
                    [i.step for i in recipe.instructions],
                    list(range(1, num_instructions + 1)),
                )
                # every ingredient/instruction should have carried through real text
                self.assertTrue(all(i.name for i in recipe.total_ingredients))
                self.assertTrue(all(i.description for i in recipe.instructions))

    def test_is_recipe_page_false_for_non_recipe_page(self):
        html = _load_fixture("non_recipe_page.html")
        for _, transformer_cls, *_ in self.CASES:
            with self.subTest(transformer=transformer_cls.__name__):
                self.assertFalse(transformer_cls().is_recipe_page(html))

    def test_transform_returns_none_for_non_recipe_page(self):
        html = _load_fixture("non_recipe_page.html")
        for _, transformer_cls, *_ in self.CASES:
            with self.subTest(transformer=transformer_cls.__name__):
                self.assertIsNone(transformer_cls().transform(html, url="https://example.com/list"))


class AllRecipesCssFallbackTest(unittest.TestCase):
    """AllRecipesTransformer's CSS-selector fallback, exercised on a page with no JSON-LD."""

    def test_fallback_is_recipe_page(self):
        html = _load_fixture("allrecipes_recipe_no_jsonld.html")
        self.assertTrue(AllRecipesTransformer().is_recipe_page(html))

    def test_fallback_transform_extracts_recipe(self):
        html = _load_fixture("allrecipes_recipe_no_jsonld.html")
        recipe = AllRecipesTransformer().transform(html, url="https://www.allrecipes.com/recipe/16354/easy-meatloaf/")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.name, "Easy Meatloaf")
        self.assertEqual(len(recipe.total_ingredients), 9)
        self.assertEqual(len(recipe.instructions), 5)
        self.assertEqual(recipe.instructions[0].description.startswith("Gather the ingredients"), True)

    def test_fallback_is_recipe_page_false_without_ingredients_block(self):
        self.assertFalse(AllRecipesTransformer().is_recipe_page("<html><body><h1>Nope</h1></body></html>"))


class TransformerRegistryTest(unittest.TestCase):
    def test_registry_covers_all_four_sources(self):
        registry = default_transformers()
        self.assertEqual(
            set(registry.keys()),
            {
                Source.ALL_RECIPES.value,
                Source.DELISH.value,
                Source.FOOD_NETWORK.value,
                Source.FOOD_DOT_COM.value,
            },
        )
        for transformer in registry.values():
            self.assertTrue(hasattr(transformer, "transform"))
            self.assertTrue(hasattr(transformer, "is_recipe_page"))


if __name__ == "__main__":
    unittest.main()
