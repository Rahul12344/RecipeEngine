"""
Tests for store/recipe_store.py: the save/get/list API and, most
importantly, that a Recipe (with nested RecipeIngredient/RecipeInstruction
frozen dataclasses) round-trips correctly through JSON serialization and
back into real dataclass instances (not just plain dicts).

No local Postgres was reachable in this environment (checked
127.0.0.1:5432; connection refused), so these tests run against
store/tests/fake_asyncpg.FakeAsyncpgPool -- a small in-memory fake of the
exact asyncpg surface AsyncPostgresStore uses -- patched in place of
asyncpg.create_pool, rather than being skipped. If Postgres *is* reachable
(e.g. in CI or on a dev machine with it running), LivePostgresRecipeStoreTest
below additionally runs a real integration test against it.
"""
import socket
import unittest
from datetime import datetime, timezone
from unittest import mock
from unittest.mock import AsyncMock, patch

from async_store.indexed_postgres_store import IndexedColumn, IndexedPostgresStore
from di import container, reset_container
from models.output_data_models.annotation_model_features import (
    Recipe,
    RecipeIngredient,
    RecipeInstruction,
)
from models.output_data_models.stored_recipe import StoredRecipe
from store.postgres.recipe_backing_store import build_recipe_backing_store  # noqa: F401 (registers with DI)
from store.recipe_store import RecipeStore, recipe_id_for_url
from store.tests.fake_asyncpg import FakeAsyncpgPool


def _postgres_reachable(host: str = "127.0.0.1", port: int = 5432, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _sample_recipe() -> Recipe:
    return Recipe(
        name="Easy Meatloaf",
        total_ingredients=[
            RecipeIngredient(name="ground beef", quantity=1.5, unit="pounds", process=None),
            RecipeIngredient(name="onion", quantity=1.0, unit="", process="chopped"),
        ],
        instructions=[
            RecipeInstruction(
                step=1,
                description="Preheat the oven to 350 degrees F.",
                list_of_ingredients_for_step=[],
            ),
            RecipeInstruction(
                step=2,
                description="Combine ground beef and onion.",
                list_of_ingredients_for_step=[
                    RecipeIngredient(name="ground beef", quantity=1.5, unit="pounds", process=None),
                ],
            ),
        ],
    )


class RecipeIdTest(unittest.TestCase):
    def test_id_is_stable_for_the_same_url(self):
        url = "https://www.allrecipes.com/recipe/16354/easy-meatloaf/"
        self.assertEqual(recipe_id_for_url(url), recipe_id_for_url(url))

    def test_id_differs_for_different_urls(self):
        self.assertNotEqual(
            recipe_id_for_url("https://example.com/a"),
            recipe_id_for_url("https://example.com/b"),
        )


class RecipeSerializationRoundTripTest(unittest.TestCase):
    """Pure serialize/deserialize round trip, no store/DB involved."""

    def test_round_trip_preserves_all_fields_and_types(self):
        recipe = _sample_recipe()
        data = recipe.to_dict()
        restored = Recipe.from_dict(data)

        self.assertEqual(restored, recipe)
        self.assertIsInstance(restored, Recipe)
        self.assertTrue(all(isinstance(i, RecipeIngredient) for i in restored.total_ingredients))
        self.assertTrue(all(isinstance(i, RecipeInstruction) for i in restored.instructions))
        self.assertTrue(
            all(
                isinstance(i, RecipeIngredient)
                for instr in restored.instructions
                for i in instr.list_of_ingredients_for_step
            )
        )

    def test_round_trip_survives_actual_json_dumps_loads(self):
        import json

        recipe = _sample_recipe()
        json_text = json.dumps(recipe.to_dict())
        restored = Recipe.from_dict(json.loads(json_text))
        self.assertEqual(restored, recipe)

    def test_round_trip_with_empty_ingredients_and_instructions(self):
        recipe = Recipe(name="Empty", total_ingredients=[], instructions=[])
        restored = Recipe.from_dict(recipe.to_dict())
        self.assertEqual(restored, recipe)

    def test_round_trip_preserves_optional_process_field(self):
        recipe = Recipe(
            name="R",
            total_ingredients=[RecipeIngredient(name="salt", quantity=1.0, unit="tsp", process=None)],
            instructions=[],
        )
        restored = Recipe.from_dict(recipe.to_dict())
        self.assertIsNone(restored.total_ingredients[0].process)


class FakePostgresRecipeStoreTest(unittest.IsolatedAsyncioTestCase):
    """Exercises RecipeStore's real SQL + connection-pool code against a fake asyncpg pool."""

    async def asyncSetUp(self):
        self.fake_pool = FakeAsyncpgPool()
        self._patcher = patch(
            "async_store.async_postgres_store.asyncpg.create_pool",
            new=AsyncMock(return_value=self.fake_pool),
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

        self._env_patcher = mock.patch.dict(
            "os.environ", {"RECIPE_ENGINE_DATABASE_URL": "postgresql://fake/db"}
        )
        self._env_patcher.start()
        self.addCleanup(self._env_patcher.stop)

        # Resolved through the real DI container end to end (RecipeStore <-
        # recipe_backing_store <- database_url), not hand-assembled, so a
        # regression anywhere in that chain would show up here too.
        reset_container()
        self.addCleanup(reset_container)
        self.store = container().get(RecipeStore)

    async def test_save_then_get_round_trips_a_real_recipe(self):
        recipe = _sample_recipe()
        url = "https://www.allrecipes.com/recipe/16354/easy-meatloaf/"

        recipe_id = await self.store.save_recipe(recipe, source="all_recipes", url=url)
        self.assertEqual(recipe_id, recipe_id_for_url(url))

        stored = await self.store.get_recipe(recipe_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.id, recipe_id)
        self.assertEqual(stored.source, "all_recipes")
        self.assertEqual(stored.url, url)
        self.assertEqual(stored.name, recipe.name)
        self.assertIsInstance(stored.ingested_at, datetime)
        self.assertEqual(stored.recipe, recipe)

    async def test_get_by_url_finds_the_same_row_as_get_recipe(self):
        recipe = _sample_recipe()
        url = "https://www.delish.com/cooking/recipe-ideas/a1/example/"
        await self.store.save_recipe(recipe, source="delish", url=url)

        stored = await self.store.get_by_url(url)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.recipe, recipe)

    async def test_get_recipe_returns_none_when_missing(self):
        self.assertIsNone(await self.store.get_recipe("does-not-exist"))

    async def test_save_recipe_upserts_on_the_same_url(self):
        url = "https://www.food.com/recipe/example-1"
        first = Recipe(name="First Version", total_ingredients=[], instructions=[])
        second = Recipe(name="Updated Version", total_ingredients=[], instructions=[])

        id1 = await self.store.save_recipe(first, source="food_dot_com", url=url)
        id2 = await self.store.save_recipe(second, source="food_dot_com", url=url)

        self.assertEqual(id1, id2)
        stored = await self.store.get_recipe(id1)
        self.assertEqual(stored.name, "Updated Version")
        self.assertEqual(len(self.fake_pool.tables["recipes"]), 1)

    async def test_list_recipes_filters_by_source_and_orders_newest_first(self):
        await self.store.save_recipe(
            Recipe(name="AR Recipe", total_ingredients=[], instructions=[]),
            source="all_recipes",
            url="https://www.allrecipes.com/recipe/1",
        )
        await self.store.save_recipe(
            Recipe(name="FN Recipe 1", total_ingredients=[], instructions=[]),
            source="food_network",
            url="https://www.foodnetwork.com/recipes/1",
        )
        await self.store.save_recipe(
            Recipe(name="FN Recipe 2", total_ingredients=[], instructions=[]),
            source="food_network",
            url="https://www.foodnetwork.com/recipes/2",
        )

        fn_recipes = await self.store.list_recipes(source="food_network")
        self.assertEqual({r.name for r in fn_recipes}, {"FN Recipe 1", "FN Recipe 2"})
        self.assertTrue(all(r.source == "food_network" for r in fn_recipes))

        all_recipes = await self.store.list_recipes()
        self.assertEqual(len(all_recipes), 3)
        # newest-ingested-first ordering
        self.assertEqual(
            [r.ingested_at for r in all_recipes],
            sorted([r.ingested_at for r in all_recipes], reverse=True),
        )

    async def test_list_recipes_respects_limit_and_offset(self):
        for i in range(5):
            await self.store.save_recipe(
                Recipe(name=f"Recipe {i}", total_ingredients=[], instructions=[]),
                source="all_recipes",
                url=f"https://www.allrecipes.com/recipe/{i}",
            )
        page = await self.store.list_recipes(source="all_recipes", limit=2, offset=1)
        self.assertEqual(len(page), 2)

    async def test_missing_connection_string_raises_a_clear_error(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            reset_container()
            store = container().get(RecipeStore)
            with self.assertRaises(RuntimeError):
                await store.get_recipe("anything")


@unittest.skipUnless(_postgres_reachable(), "no local Postgres reachable on 127.0.0.1:5432")
class LivePostgresRecipeStoreTest(unittest.IsolatedAsyncioTestCase):
    """Real integration test, only runs when a local Postgres is actually up."""

    async def asyncSetUp(self):
        import os

        connection_string = os.environ.get(
            "RECIPE_ENGINE_TEST_DATABASE_URL",
            "postgresql://postgres@127.0.0.1:5432/postgres",
        )
        # Same shape as build_recipe_backing_store(), but pointed at an
        # isolated fixture table rather than the real "recipes" table.
        self.backing_store = IndexedPostgresStore(
            connection_string=connection_string,
            table_name="recipes_test_fixture",
            key_column="id",
            extra_columns=(
                IndexedColumn("source", extract=lambda stored: stored.source),
                IndexedColumn("url", extract=lambda stored: stored.url, unique=True),
                IndexedColumn("name", extract=lambda stored: stored.name),
                IndexedColumn("ingested_at", extract=lambda stored: stored.ingested_at, sql_type="TIMESTAMPTZ"),
            ),
            serialize=lambda stored: stored.recipe.to_dict(),
            deserialize=lambda row: StoredRecipe(
                id=row["id"],
                source=row["source"],
                url=row["url"],
                name=row["name"],
                ingested_at=row["ingested_at"],
                recipe=Recipe.from_dict(row["data"]),
            ),
        )
        self.store = RecipeStore(recipe_backing_store=self.backing_store)
        pool = await self.backing_store._ensure_connection()
        async with pool.acquire() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {self.backing_store.table_name}")
        await self.backing_store._create_table_if_not_exists()

    async def asyncTearDown(self):
        pool = await self.backing_store._ensure_connection()
        async with pool.acquire() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {self.backing_store.table_name}")
        await self.backing_store.close()

    async def test_save_and_get_round_trip_against_real_postgres(self):
        recipe = _sample_recipe()
        url = "https://www.allrecipes.com/recipe/16354/easy-meatloaf/"
        recipe_id = await self.store.save_recipe(recipe, source="all_recipes", url=url)
        stored = await self.store.get_recipe(recipe_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.recipe, recipe)


if __name__ == "__main__":
    unittest.main()
