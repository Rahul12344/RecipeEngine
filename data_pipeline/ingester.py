from __future__ import annotations

import asyncio
import logging
from typing import Optional

import aioboto3

from di import provides
from data_pipeline.retriever.recipe_source_retrievers import BaseRetriever, RawRecipeData
from data_pipeline.meta_info.source_metadata import SourceMetadata
from data_pipeline.transformers.recipe_transformer_interface import RecipeTransformerInterface
from store.recipe_store import RecipeStore

logger = logging.getLogger(__name__)


@provides("ingester")
class Ingester:
    """
    Scrapes each supported source and, for every recipe page found:
      1. archives the raw HTML to S3 (original behavior), and
      2. runs it through the matching transformer and persists the parsed
         Recipe via `recipe_store` (skipped if no transformer is registered
         for that source, or if `recipe_store` isn't provided -- keeping the
         raw-archive-only behavior available for callers that don't want
         parsing).
    """

    def __init__(
        self,
        recipe_source_retriever: BaseRetriever,
        supported_sources: list[SourceMetadata],
        transformers: Optional[dict[str, RecipeTransformerInterface]] = None,
        recipe_store: Optional[RecipeStore] = None,
    ):
        self._recipe_source_retriever = recipe_source_retriever
        self._supported_sources = supported_sources
        self._transformers = transformers or {}
        self._recipe_store = recipe_store

    async def ingest(self) -> None:
        tasks = []

        session = aioboto3.Session()
        async with session.client('s3') as s3:
            for source_metadata in self._supported_sources:
                async for recipe in self._recipe_source_retriever.scrape(source_metadata):
                    tasks.append(self._archive_raw_html(recipe, s3))
                    tasks.append(self._transform_and_store(recipe))

            await asyncio.gather(*tasks)

    async def _archive_raw_html(self, recipe: RawRecipeData, s3_client) -> None:
        await s3_client.put_object(
            Bucket='recipe-data',
            Key=f'{recipe.source}/{recipe.url.split("/")[-1]}',
            Body=recipe.html
        )

    async def _transform_and_store(self, recipe: RawRecipeData) -> None:
        if self._recipe_store is None:
            return

        transformer = self._transformers.get(recipe.source)
        if transformer is None:
            logger.debug(f"No transformer registered for source '{recipe.source}'; skipping {recipe.url}")
            return

        try:
            if not transformer.is_recipe_page(recipe.html):
                logger.debug(f"{recipe.url} was not recognized as a recipe page by its transformer")
                return
            parsed_recipe = transformer.transform(recipe.html, recipe.url)
        except Exception as e:
            logger.error(f"Error transforming {recipe.url}: {e}", exc_info=True)
            return

        if parsed_recipe is None:
            logger.warning(f"Transformer could not extract a Recipe from {recipe.url}")
            return

        try:
            await self._recipe_store.save_recipe(parsed_recipe, source=recipe.source, url=recipe.url)
        except Exception as e:
            logger.error(f"Error saving recipe parsed from {recipe.url}: {e}", exc_info=True)
