import asyncio
import aioboto3

from data_pipeline.retriever.recipe_source_retrievers import BaseRetriever
from data_pipeline.meta_info.source_metadata import AllRecipesSourceMetadata, SourceMetadata

class Ingester:
    def __init__(self, recipe_source_retriever: BaseRetriever, supported_sources: list[SourceMetadata]):
        self._recipe_source_retriever = recipe_source_retriever
        self._supported_sources = supported_sources

    async def ingest(self) -> None:
        tasks = []

        session = aioboto3.Session()
        async with session.client('s3') as s3:
            for source_metadata in self._supported_sources:
                async for recipe in self._recipe_source_retriever.scrape(source_metadata):
                    tasks.append(self._save_recipe(recipe, s3))

            await asyncio.gather(*tasks)

    async def _save_recipe(self, recipe: RawRecipeData, session: aioboto3.Session) -> None:
        await session.put_object(
            Bucket='recipe-data',
            Key=f'{recipe.source}/{recipe.url.split("/")[-1]}',
            Body=recipe.html
        )