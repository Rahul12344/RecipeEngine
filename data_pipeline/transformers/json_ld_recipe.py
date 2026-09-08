"""
Shared schema.org Recipe JSON-LD extraction logic.

Every source currently supported by this pipeline (AllRecipes, Delish,
FoodNetwork, Food.com) embeds a <script type="application/ld+json"> block
describing the recipe with the schema.org `Recipe` vocabulary -- publishers
do this so Google can show Recipe rich results. That makes it a far more
robust extraction target than hand-rolled CSS selectors (which break the
moment a site redesigns its markup), and the parsing logic below is shared
across all 4 sources rather than duplicated per-site.

Verified by hand against a live/archived example page from each of the 4
sites while building this pipeline (see data_pipeline/transformers/tests/
fixtures for trimmed, real excerpts of what was found).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from bs4 import BeautifulSoup

from models.output_data_models.annotation_model_features import (
    Recipe,
    RecipeIngredient,
    RecipeInstruction,
)

logger = logging.getLogger(__name__)


def _iter_json_ld_objects(soup: BeautifulSoup):
    """Yield every JSON-LD object embedded in the page, flattening @graph wrappers."""
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for candidate in candidates:
            if isinstance(candidate, dict) and isinstance(candidate.get("@graph"), list):
                for item in candidate["@graph"]:
                    if isinstance(item, dict):
                        yield item
            elif isinstance(candidate, dict):
                yield candidate


def _is_recipe_type(item: dict) -> bool:
    item_type = item.get("@type")
    if isinstance(item_type, str):
        return item_type == "Recipe"
    if isinstance(item_type, list):
        return "Recipe" in item_type
    return False


def find_recipe_json_ld(html: str) -> Optional[dict]:
    """
    Find the first schema.org Recipe JSON-LD object embedded in an HTML page.

    Returns the raw dict (schema.org fields, e.g. name/recipeIngredient/
    recipeInstructions) or None if no Recipe block is present / parseable.
    """
    soup = BeautifulSoup(html, "html.parser")
    for item in _iter_json_ld_objects(soup):
        if _is_recipe_type(item):
            return item
    return None


def _flatten_ingredients(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _flatten_instructions(raw: Any) -> list[str]:
    """
    Normalize the several shapes `recipeInstructions` can legally take under
    schema.org into a flat, ordered list of step description strings:
      - a single free-text string (occasionally newline-separated steps)
      - a list of plain strings
      - a list of HowToStep objects (each with a "text" field)
      - a list of HowToSection objects, each with an "itemListElement" of
        HowToStep objects (recursed into)
    """
    if raw is None:
        return []

    if isinstance(raw, str):
        parts = [part.strip() for part in raw.replace("\r\n", "\n").split("\n") if part.strip()]
        return parts if parts else ([raw.strip()] if raw.strip() else [])

    if isinstance(raw, dict):
        raw = [raw]

    steps: list[str] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, str):
                text = entry.strip()
                if text:
                    steps.append(text)
            elif isinstance(entry, dict):
                if "itemListElement" in entry:
                    steps.extend(_flatten_instructions(entry.get("itemListElement")))
                else:
                    text = entry.get("text") or entry.get("name")
                    if text:
                        steps.append(str(text).strip())
    return steps


def recipe_from_json_ld(item: dict) -> Optional[Recipe]:
    """Build a `Recipe` from a raw schema.org Recipe JSON-LD dict, or None if unusable."""
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()

    ingredient_strs = _flatten_ingredients(item.get("recipeIngredient") or item.get("ingredients"))
    instruction_strs = _flatten_instructions(item.get("recipeInstructions"))

    ingredients = [
        RecipeIngredient(name=raw, quantity=0.0, unit="", process=None)
        for raw in ingredient_strs
    ]
    instructions = [
        RecipeInstruction(step=step_num, description=text, list_of_ingredients_for_step=[])
        for step_num, text in enumerate(instruction_strs, start=1)
    ]

    return Recipe(name=name, total_ingredients=ingredients, instructions=instructions)
