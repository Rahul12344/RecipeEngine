#!/usr/bin/env python
"""
One-shot ingestion pass across all supported recipe sources.

For each of AllRecipes, Delish, FoodNetwork, and Food.com, this crawls the
site (BaseRetriever), archives every recipe page's raw HTML to S3, and parses
+ persists structured Recipe data to Postgres (data_pipeline.Ingester +
store.recipe_store.RecipeStore). It runs a single full pass and exits -- it
is meant to be triggered by an external, OS-level scheduler (cron or
launchd), not run as a long-lived process. See the "Scheduling ingestion"
section of the repo README for how to wire that up.

Usage:
    python scripts/run_ingestion.py

Required environment variable:
    RECIPE_ENGINE_DATABASE_URL - Postgres connection string, e.g.
        postgresql://user:password@localhost:5432/recipe_engine

AWS credentials for the S3 archive step are picked up from the standard
boto3 credential chain (env vars / ~/.aws/credentials / instance role).

Exit codes:
    0 - the ingestion run completed (a given recipe's transform/store/archive
        failure is logged and skipped, not fatal -- see data_pipeline/ingester.py)
    1 - the run could not proceed at all (e.g. missing configuration, or an
        unhandled error escaping the ingestion pass)
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Allow running this script directly (`python scripts/run_ingestion.py`)
# without requiring the repo root to already be on PYTHONPATH.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.ingester import Ingester  # noqa: E402
from data_pipeline.meta_info.allrecipes_source_metadata import AllRecipesSourceMetadata  # noqa: E402
from data_pipeline.meta_info.delish_source_metadata import DelishSourceMetadata  # noqa: E402
from data_pipeline.meta_info.food_dot_com_source_metadata import FoodDotComSourceMetadata  # noqa: E402
from data_pipeline.meta_info.food_network_source_metadata import FoodNetworkSourceMetadata  # noqa: E402
from data_pipeline.retriever.recipe_source_retrievers import BaseRetriever  # noqa: E402
from data_pipeline.transformers.transformer_registry import default_transformers  # noqa: E402
from async_store.indexed_postgres_store import DATABASE_URL_ENV_VAR  # noqa: E402
from store.recipe_store import RecipeStore  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _run() -> None:
    database_url = os.environ.get(DATABASE_URL_ENV_VAR)
    if not database_url:
        raise RuntimeError(
            f"{DATABASE_URL_ENV_VAR} is not set (a Postgres connection string, "
            f"e.g. postgresql://user:password@localhost:5432/recipe_engine)."
        )

    recipe_store = RecipeStore(connection_string=database_url)
    retriever = BaseRetriever()
    supported_sources = [
        AllRecipesSourceMetadata(),
        DelishSourceMetadata(),
        FoodNetworkSourceMetadata(),
        FoodDotComSourceMetadata(),
    ]

    ingester = Ingester(
        recipe_source_retriever=retriever,
        supported_sources=supported_sources,
        transformers=default_transformers(),
        recipe_store=recipe_store,
    )

    logger.info(f"Starting ingestion pass across {len(supported_sources)} sources")
    try:
        await ingester.ingest()
    finally:
        await recipe_store.close()


def main() -> int:
    try:
        asyncio.run(_run())
    except Exception:
        logger.exception("Ingestion run failed")
        return 1
    logger.info("Ingestion run completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
