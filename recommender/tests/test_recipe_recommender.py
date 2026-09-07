import unittest

from models.features.user_ingredient_inventory import InventoryItem, UserIngredientInventory
from models.output_data_models.annotation_model_features import Recipe, RecipeIngredient
from pipelines.pipeline import Pipeline
from recommender.inventory_match_step import InventoryMatchStep
from recommender.recipe_catalog import InMemoryRecipeCatalog
from recommender.recipe_recommender import RecipeRecommender
from recommender.recommendation_options import RecommendationOptions
from recommender.user import User


def _recipe(name: str, ingredient_names: list) -> Recipe:
    return Recipe(
        name=name,
        total_ingredients=[
            RecipeIngredient(name=n, quantity=1.0, unit="unit") for n in ingredient_names
        ],
        instructions=[],
    )


class RecipeRecommenderEndToEndTest(unittest.TestCase):
    def setUp(self):
        self.pancakes = _recipe("Pancakes", ["flour", "egg", "milk"])
        self.omelette = _recipe("Omelette", ["egg", "cheese"])
        self.steak = _recipe("Steak", ["beef", "pepper", "garlic"])

        catalog = InMemoryRecipeCatalog([self.steak, self.pancakes, self.omelette])
        pipeline = Pipeline(steps=[InventoryMatchStep(recipe_catalog=catalog)])
        self.recommender = RecipeRecommender(recommender_pipeline=pipeline)

        self.user = User(
            user_id="u1",
            inventory=UserIngredientInventory(
                user_id="u1",
                items=[
                    InventoryItem(name="eggs", quantity=6, unit="count"),
                    InventoryItem(name="cheese", quantity=200, unit="g"),
                ],
            ),
        )

    def test_ranks_readiest_recipe_first(self):
        result = self.recommender(self.user, RecommendationOptions())
        # Omelette: 2/2 ingredients on hand -> ranked first.
        # Pancakes: 1/3 on hand.
        # Steak: 0/3 on hand.
        self.assertEqual([r.name for r in result], ["Omelette", "Pancakes", "Steak"])

    def test_limit_is_applied_end_to_end(self):
        result = self.recommender(self.user, RecommendationOptions(limit=1))
        self.assertEqual([r.name for r in result], ["Omelette"])

    def test_min_match_ratio_filters_out_unmakeable_recipes(self):
        result = self.recommender(self.user, RecommendationOptions(min_match_ratio=1.0))
        self.assertEqual([r.name for r in result], ["Omelette"])


if __name__ == "__main__":
    unittest.main()
