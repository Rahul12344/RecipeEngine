"""
Generic RecipeTransformerInterface implementation driven by embedded
schema.org Recipe JSON-LD, shared across all supported sources.

Subclasses may override `_fallback_transform` / `_fallback_is_recipe_page`
to add source-specific CSS-selector extraction for pages that lack usable
JSON-LD; by default there is no fallback (JSON-LD absent == not a recipe).
"""
from __future__ import annotations

import logging
from typing import Optional

from data_pipeline.transformers.json_ld_recipe import (
    find_recipe_json_ld,
    recipe_from_json_ld,
)
from data_pipeline.transformers.recipe_transformer_interface import RecipeTransformerInterface
from models.output_data_models.annotation_model_features import Recipe

logger = logging.getLogger(__name__)


class JsonLdRecipeTransformer(RecipeTransformerInterface):
    """
    Transformer that extracts Recipe data primarily from embedded schema.org
    Recipe JSON-LD, falling back to source-specific CSS-selector scraping
    (via the `_fallback_*` hooks) only when JSON-LD isn't usable.
    """

    def transform(self, html: str, url: str) -> Optional[Recipe]:
        try:
            json_ld = find_recipe_json_ld(html)
        except Exception as e:
            logger.error(f"Error parsing JSON-LD from {url}: {e}", exc_info=True)
            json_ld = None

        if json_ld is not None:
            try:
                recipe = recipe_from_json_ld(json_ld)
            except Exception as e:
                logger.error(f"Error building Recipe from JSON-LD at {url}: {e}", exc_info=True)
                recipe = None
            if recipe is not None:
                return recipe
            logger.warning(f"JSON-LD Recipe block at {url} was not usable; trying fallback extraction")

        try:
            return self._fallback_transform(html, url)
        except Exception as e:
            logger.error(f"Error in fallback transform for {url}: {e}", exc_info=True)
            return None

    def is_recipe_page(self, html: str) -> bool:
        try:
            if find_recipe_json_ld(html) is not None:
                return True
        except Exception as e:
            logger.error(f"Error checking JSON-LD for recipe page: {e}")

        try:
            return self._fallback_is_recipe_page(html)
        except Exception as e:
            logger.error(f"Error in fallback is_recipe_page check: {e}")
            return False

    def _fallback_transform(self, html: str, url: str) -> Optional[Recipe]:
        """Override to provide CSS-selector fallback extraction for this source."""
        return None

    def _fallback_is_recipe_page(self, html: str) -> bool:
        """Override to provide CSS-selector fallback recipe-page detection for this source."""
        return False
