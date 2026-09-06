import unittest

from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory
from models.output_data_models.annotation_model_features import Recipe, RecipeIngredient
from recommender.inventory_match_step import (
    InventoryMatchStep,
    rank_recipes_by_inventory,
    score_recipe,
)
from recommender.recipe_catalog import InMemoryRecipeCatalog
from recommender.recommendation_options import RecommendationOptions
from recommender.user import User


def _ingredient(name: str) -> RecipeIngredient:
    return RecipeIngredient(name=name, quantity=1.0, unit="unit")


def _recipe(name: str, ingredient_names: list) -> Recipe:
    return Recipe(
        name=name,
        total_ingredients=[_ingredient(n) for n in ingredient_names],
        instructions=[],
    )


def _inventory(user_id: str, item_names: list) -> UserIngredientInventory:
    return UserIngredientInventory(
        user_id=user_id,
        items=[InventoryItem(name=n, quantity=None, unit=None) for n in item_names],
    )


class ScoreRecipeTest(unittest.TestCase):
    def test_full_coverage_scores_one(self):
        recipe = _recipe("Salad", ["lettuce", "tomato", "cucumber"])
        score = score_recipe(recipe, ["lettuce", "tomatoes", "cucumbers"])
        self.assertEqual(score.matched_count, 3)
        self.assertEqual(score.total_count, 3)
        self.assertEqual(score.match_ratio, 1.0)
        self.assertEqual(score.missing_ingredients, [])
        self.assertEqual(score.missing_count, 0)

    def test_partial_coverage(self):
        recipe = _recipe("Omelette", ["egg", "cheese", "milk"])
        score = score_recipe(recipe, ["eggs"])
        self.assertEqual(score.matched_count, 1)
        self.assertEqual(score.total_count, 3)
        self.assertAlmostEqual(score.match_ratio, 1 / 3)
        self.assertEqual(score.missing_ingredients, ["cheese", "milk"])
        self.assertEqual(score.missing_count, 2)

    def test_no_coverage(self):
        recipe = _recipe("Steak", ["beef", "pepper"])
        score = score_recipe(recipe, ["tofu"])
        self.assertEqual(score.matched_count, 0)
        self.assertEqual(score.match_ratio, 0.0)
        self.assertEqual(score.missing_count, 2)

    def test_recipe_with_no_ingredients_is_trivially_complete(self):
        recipe = _recipe("Water", [])
        score = score_recipe(recipe, [])
        self.assertEqual(score.total_count, 0)
        self.assertEqual(score.match_ratio, 1.0)
        self.assertEqual(score.missing_count, 0)

    def test_tolerant_matching_handles_pluralization_and_qualifiers(self):
        recipe = _recipe("Sauce", ["tomatoes"])
        score = score_recipe(recipe, ["roma tomato"])
        self.assertEqual(score.matched_count, 1)

    def test_word_boundary_avoids_false_positive(self):
        recipe = _recipe("Curry", ["eggplant"])
        score = score_recipe(recipe, ["egg"])
        self.assertEqual(score.matched_count, 0)
        self.assertEqual(score.missing_ingredients, ["eggplant"])


class RankRecipesByInventoryTest(unittest.TestCase):
    def test_ranks_by_descending_match_ratio(self):
        full_match = _recipe("Full", ["salt", "pepper"])
        half_match = _recipe("Half", ["salt", "pepper", "cumin", "paprika"])
        no_match = _recipe("None", ["saffron", "truffle"])

        inventory = _inventory("u1", ["salt", "pepper"])
        ranked = rank_recipes_by_inventory([half_match, no_match, full_match], inventory)

        self.assertEqual([s.recipe.name for s in ranked], ["Full", "Half", "None"])
        self.assertEqual(ranked[0].match_ratio, 1.0)
        self.assertEqual(ranked[2].match_ratio, 0.0)

    def test_ties_broken_by_fewest_missing_ingredients(self):
        # Both recipes have a 50% match ratio (1/2), but "FewerMissing" is
        # missing fewer ingredients in absolute terms... actually with equal
        # ratios and equal counts we instead verify a genuine ratio tie with
        # differing missing counts is impossible at equal totals, so use
        # differing totals that produce the same ratio.
        two_of_four = _recipe("TwoOfFour", ["salt", "pepper", "cumin", "paprika"])  # 2/4 = 0.5
        one_of_two = _recipe("OneOfTwo", ["salt", "cumin"])  # 1/2 = 0.5

        inventory = _inventory("u1", ["salt", "pepper"])
        ranked = rank_recipes_by_inventory([two_of_four, one_of_two], inventory)

        # Both have match_ratio 0.5; "OneOfTwo" is missing only 1 ingredient
        # vs "TwoOfFour" missing 2, so it should be ranked first.
        self.assertEqual(ranked[0].recipe.name, "OneOfTwo")
        self.assertEqual(ranked[0].missing_count, 1)
        self.assertEqual(ranked[1].recipe.name, "TwoOfFour")
        self.assertEqual(ranked[1].missing_count, 2)

    def test_empty_recipe_list(self):
        self.assertEqual(rank_recipes_by_inventory([], _inventory("u1", ["salt"])), [])

    def test_empty_inventory_ranks_zero_ingredient_recipes_first(self):
        has_ingredients = _recipe("Soup", ["stock", "carrot"])
        no_ingredients = _recipe("Ice Water", [])

        ranked = rank_recipes_by_inventory([has_ingredients, no_ingredients], _inventory("u1", []))
        self.assertEqual(ranked[0].recipe.name, "Ice Water")
        self.assertEqual(ranked[1].recipe.name, "Soup")


class InventoryMatchStepTest(unittest.TestCase):
    def setUp(self):
        self.full_match = _recipe("Full", ["salt", "pepper"])
        self.half_match = _recipe("Half", ["salt", "pepper", "cumin", "paprika"])
        self.no_match = _recipe("None", ["saffron", "truffle"])
        self.catalog = InMemoryRecipeCatalog([self.half_match, self.no_match, self.full_match])
        self.user = User(user_id="u1", inventory=_inventory("u1", ["salt", "pepper"]))
        self.step = InventoryMatchStep(recipe_catalog=self.catalog)

    def test_returns_ranked_recipes(self):
        result = self.step((self.user, RecommendationOptions()))
        self.assertEqual([r.name for r in result], ["Full", "Half", "None"])

    def test_respects_limit(self):
        result = self.step((self.user, RecommendationOptions(limit=1)))
        self.assertEqual([r.name for r in result], ["Full"])

    def test_respects_min_match_ratio(self):
        result = self.step((self.user, RecommendationOptions(min_match_ratio=0.5)))
        self.assertEqual([r.name for r in result], ["Full", "Half"])

    def test_empty_catalog_returns_empty_list(self):
        step = InventoryMatchStep(recipe_catalog=InMemoryRecipeCatalog([]))
        result = step((self.user, RecommendationOptions()))
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
