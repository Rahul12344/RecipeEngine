"""
Tests that Ingester actually wires the transform+store step in (not dead
code) alongside the pre-existing S3 raw-HTML archive, using fakes for the
retriever, transformers, recipe store, and S3 client -- no real network or
AWS calls.
"""
import unittest
from unittest.mock import patch

from data_pipeline.ingester import Ingester
from data_pipeline.meta_info.source_metadata import SourceMetadata
from data_pipeline.retriever.recipe_source_retrievers import RawRecipeData
from data_pipeline.transformers.recipe_transformer_interface import RecipeTransformerInterface
from models.output_data_models.annotation_model_features import Recipe


class _FakeSourceMetadata(SourceMetadata):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def hostname(self) -> str:
        return f"https://{self._name}.example.com"

    @property
    def recipe_identifier(self) -> str:
        return "/recipe/"

    @property
    def recipe_link_pattern(self) -> set[str]:
        return {"/recipe/"}


class _FakeRetriever:
    """Yields a canned set of RawRecipeData per source, standing in for BaseRetriever."""

    def __init__(self, pages_by_source: dict[str, list[RawRecipeData]]):
        self._pages_by_source = pages_by_source

    async def scrape(self, source_metadata: SourceMetadata):
        for page in self._pages_by_source.get(source_metadata.name, []):
            yield page


class _FakeTransformer(RecipeTransformerInterface):
    """Always recognizes and 'transforms' a page into a fixed Recipe."""

    def __init__(self, recipe: Recipe):
        self._recipe = recipe

    def transform(self, html, url):
        return self._recipe

    def is_recipe_page(self, html):
        return True


class _FailingTransformer(RecipeTransformerInterface):
    """Simulates a source whose transformer can't extract anything."""

    def transform(self, html, url):
        return None

    def is_recipe_page(self, html):
        return True


class _FakeRecipeStore:
    def __init__(self):
        self.saved: list[tuple] = []

    async def save_recipe(self, recipe, source, url):
        self.saved.append((recipe, source, url))
        return "fake-id"


class _FakeS3Client:
    def __init__(self):
        self.put_objects: list[dict] = []

    async def put_object(self, **kwargs):
        self.put_objects.append(kwargs)


class _FakeS3ClientContext:
    def __init__(self, client: _FakeS3Client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAioboto3Session:
    def __init__(self, client: _FakeS3Client):
        self._client = client

    def client(self, service_name):
        assert service_name == "s3"
        return _FakeS3ClientContext(self._client)


class IngesterTransformAndStoreWiringTest(unittest.IsolatedAsyncioTestCase):
    async def test_ingest_archives_raw_html_and_persists_transformed_recipe(self):
        recipe = Recipe(name="Test Recipe", total_ingredients=[], instructions=[])
        source_metadata = _FakeSourceMetadata("good_source")
        page = RawRecipeData(html="<html></html>", source="good_source", url="https://good_source.example.com/recipe/1")

        retriever = _FakeRetriever({"good_source": [page]})
        recipe_store = _FakeRecipeStore()
        s3_client = _FakeS3Client()

        ingester = Ingester(
            recipe_source_retriever=retriever,
            supported_sources=[source_metadata],
            transformers={"good_source": _FakeTransformer(recipe)},
            recipe_store=recipe_store,
        )

        with patch("data_pipeline.ingester.aioboto3.Session", return_value=_FakeAioboto3Session(s3_client)):
            await ingester.ingest()

        # raw HTML archive step still happens
        self.assertEqual(len(s3_client.put_objects), 1)
        self.assertEqual(s3_client.put_objects[0]["Bucket"], "recipe-data")
        self.assertEqual(s3_client.put_objects[0]["Body"], page.html)

        # transform+store step actually ran (not dead code)
        self.assertEqual(len(recipe_store.saved), 1)
        saved_recipe, saved_source, saved_url = recipe_store.saved[0]
        self.assertEqual(saved_recipe, recipe)
        self.assertEqual(saved_source, "good_source")
        self.assertEqual(saved_url, page.url)

    async def test_missing_transformer_for_source_still_archives_raw_html(self):
        source_metadata = _FakeSourceMetadata("unmapped_source")
        page = RawRecipeData(html="<html></html>", source="unmapped_source", url="https://unmapped_source.example.com/recipe/1")

        retriever = _FakeRetriever({"unmapped_source": [page]})
        recipe_store = _FakeRecipeStore()
        s3_client = _FakeS3Client()

        ingester = Ingester(
            recipe_source_retriever=retriever,
            supported_sources=[source_metadata],
            transformers={},  # nothing registered for this source
            recipe_store=recipe_store,
        )

        with patch("data_pipeline.ingester.aioboto3.Session", return_value=_FakeAioboto3Session(s3_client)):
            await ingester.ingest()

        self.assertEqual(len(s3_client.put_objects), 1)
        self.assertEqual(len(recipe_store.saved), 0)

    async def test_transformer_returning_none_does_not_save_but_still_archives(self):
        source_metadata = _FakeSourceMetadata("bad_source")
        page = RawRecipeData(html="<html></html>", source="bad_source", url="https://bad_source.example.com/recipe/1")

        retriever = _FakeRetriever({"bad_source": [page]})
        recipe_store = _FakeRecipeStore()
        s3_client = _FakeS3Client()

        ingester = Ingester(
            recipe_source_retriever=retriever,
            supported_sources=[source_metadata],
            transformers={"bad_source": _FailingTransformer()},
            recipe_store=recipe_store,
        )

        with patch("data_pipeline.ingester.aioboto3.Session", return_value=_FakeAioboto3Session(s3_client)):
            await ingester.ingest()

        self.assertEqual(len(s3_client.put_objects), 1)
        self.assertEqual(len(recipe_store.saved), 0)

    async def test_no_recipe_store_configured_skips_transform_but_still_archives(self):
        recipe = Recipe(name="Test Recipe", total_ingredients=[], instructions=[])
        source_metadata = _FakeSourceMetadata("good_source")
        page = RawRecipeData(html="<html></html>", source="good_source", url="https://good_source.example.com/recipe/1")

        retriever = _FakeRetriever({"good_source": [page]})
        s3_client = _FakeS3Client()

        ingester = Ingester(
            recipe_source_retriever=retriever,
            supported_sources=[source_metadata],
            transformers={"good_source": _FakeTransformer(recipe)},
            recipe_store=None,
        )

        with patch("data_pipeline.ingester.aioboto3.Session", return_value=_FakeAioboto3Session(s3_client)):
            await ingester.ingest()

        self.assertEqual(len(s3_client.put_objects), 1)


if __name__ == "__main__":
    unittest.main()
