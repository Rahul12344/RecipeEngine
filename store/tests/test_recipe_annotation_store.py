"""
Tests for store/recipe_annotation_store.py: serialize/deserialize round trip
(including the Diet/DietTag enums) and the store/get/get_by_sort_key API,
against the same FakeAsyncpgPool used for RecipeStore (see
store/tests/fake_asyncpg.py and test_recipe_store.py for why: no local
Postgres is reachable in this environment).
"""
import unittest
from unittest.mock import AsyncMock, patch

from models.output_data_models.annotation_model_features import (
    Diet,
    DietTag,
    Effort,
    Recipe,
    RecipeAnnotation,
    RecipeMetadata,
)
from store.recipe_annotation_store import (
    RecipeAnnotationStore,
    annotation_from_dict,
    annotation_to_dict,
)
from store.tests.fake_asyncpg import FakeAsyncpgPool


def _sample_annotation() -> RecipeAnnotation:
    return RecipeAnnotation(
        recipe=Recipe(
            name="Easy Meatloaf",
            total_ingredients=[],
            instructions=[],
        ),
        recipe_metadata=RecipeMetadata(
            diet=Diet.NON_VEGETARIAN,
            group="main course",
            effort=Effort(cook_time="1 hour", prep_time="15 minutes", difficulty="easy", cost="low"),
            diet_tags=[DietTag.GLUTEN_FREE, DietTag.NUT_FREE],
        ),
    )


class RecipeAnnotationSerializationRoundTripTest(unittest.TestCase):
    def test_round_trip_preserves_enums_and_nested_dataclasses(self):
        annotation = _sample_annotation()
        restored = annotation_from_dict(annotation_to_dict(annotation))
        self.assertEqual(restored, annotation)
        self.assertIsInstance(restored.recipe_metadata.diet, Diet)
        self.assertTrue(all(isinstance(t, DietTag) for t in restored.recipe_metadata.diet_tags))

    def test_round_trip_survives_actual_json_dumps_loads(self):
        import json

        annotation = _sample_annotation()
        json_text = json.dumps(annotation_to_dict(annotation))
        restored = annotation_from_dict(json.loads(json_text))
        self.assertEqual(restored, annotation)


class FakePostgresRecipeAnnotationStoreTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake_pool = FakeAsyncpgPool()
        self._patcher = patch(
            "async_store.async_postgres_store.asyncpg.create_pool",
            new=AsyncMock(return_value=self.fake_pool),
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)
        self.store = RecipeAnnotationStore(connection_string="postgresql://fake/db")

    async def test_store_then_get_round_trips(self):
        annotation = _sample_annotation()
        await self.store.store("recipe-1", annotation)

        fetched = await self.store.get("recipe-1")
        self.assertEqual(fetched, annotation)

    async def test_get_by_sort_key_finds_by_recipe_name(self):
        annotation = _sample_annotation()
        await self.store.store("recipe-1", annotation)

        fetched = await self.store.get_by_sort_key("Easy Meatloaf")
        self.assertEqual(fetched, annotation)

    async def test_get_by_sort_key_returns_none_when_missing(self):
        self.assertIsNone(await self.store.get_by_sort_key("Nonexistent"))

    async def test_missing_connection_string_raises_a_clear_error(self):
        store = RecipeAnnotationStore(connection_string=None)
        with self.assertRaises(RuntimeError):
            await store.get("anything")


if __name__ == "__main__":
    unittest.main()
