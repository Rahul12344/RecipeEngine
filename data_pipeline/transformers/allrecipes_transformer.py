import logging
from typing import Optional

from bs4 import BeautifulSoup

from data_pipeline.transformers.json_ld_recipe_transformer import JsonLdRecipeTransformer
from models.output_data_models.annotation_model_features import (
    Recipe,
    RecipeIngredient,
    RecipeInstruction,
)

logger = logging.getLogger(__name__)


class AllRecipesTransformer(JsonLdRecipeTransformer):
    """
    Transformer for extracting recipe data from AllRecipes.com HTML.

    Primary extraction is the shared schema.org Recipe JSON-LD path (see
    JsonLdRecipeTransformer) -- verified against a live AllRecipes page while
    building this pipeline (archive.org/web/.../allrecipes.com/recipe/16354/
    easy-meatloaf/, since direct fetches from this sandbox are blocked by
    AllRecipes' bot protection). That page's schema.org Recipe block round-
    tripped cleanly (name/recipeIngredient/recipeInstructions all present).

    The CSS-selector fallback below replaces the *previous* version of this
    class's selectors (e.g. `#article-heading_2-0`, `#mntl-structured-
    ingredients_1-0`, `#recipe__steps_1-0`, `.recipe-container`), which were
    hand-guessed and never verified -- checking them against the same live
    page confirmed none of those ids/classes exist any more. The selectors
    below (`.article-heading`, `.mm-recipes-structured-ingredients`,
    `.mm-recipes-steps__content`) are what that page's current markup
    actually uses, kept only as a fallback for whenever JSON-LD is missing.
    """

    def _fallback_is_recipe_page(self, html: str) -> bool:
        try:
            soup = BeautifulSoup(html, "html.parser")
            return bool(soup.find("div", class_="mm-recipes-structured-ingredients"))
        except Exception as e:
            logger.error(f"Error checking if page is recipe: {str(e)}")
            return False

    def _fallback_transform(self, html: str, url: str) -> Optional[Recipe]:
        try:
            soup = BeautifulSoup(html, "html.parser")

            name = self._get_name(soup)
            if not name:
                logger.warning(f"Could not extract recipe name from {url}")
                return None

            ingredients = self._get_ingredients(soup)
            instructions = self._get_instructions(soup)

            recipe_ingredients = self._parse_ingredients(ingredients)
            recipe_instructions = self._parse_instructions(instructions)

            return Recipe(
                name=name,
                total_ingredients=recipe_ingredients,
                instructions=recipe_instructions,
            )
        except Exception as e:
            logger.error(f"Error transforming recipe from {url}: {str(e)}", exc_info=True)
            return None

    def _get_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract recipe name from the page"""
        try:
            element = soup.find("h1", class_="article-heading")
            return element.get_text().strip(' \t\n\r') if element else None
        except Exception as e:
            logger.error(f"Error extracting name: {str(e)}")
            return None

    def _get_ingredients(self, soup: BeautifulSoup) -> list[str]:
        """Extract raw ingredient strings from the page"""
        try:
            ingredients_div = soup.find("div", class_="mm-recipes-structured-ingredients")
            if not ingredients_div:
                return []
            return [li.get_text(' ', strip=True) for li in ingredients_div.find_all("li")]
        except Exception as e:
            logger.error(f"Error extracting ingredients: {str(e)}")
            return []

    def _get_instructions(self, soup: BeautifulSoup) -> list[str]:
        """Extract raw instruction strings from the page"""
        try:
            steps_div = soup.find("div", class_="mm-recipes-steps__content")
            if not steps_div:
                return []
            steps = []
            for li in steps_div.find_all("li"):
                # Each step <li> also embeds a <figure> with image captions;
                # the step text itself lives in a <p>.
                paragraph = li.find("p")
                text = paragraph.get_text(' ', strip=True) if paragraph else li.get_text(' ', strip=True)
                if text:
                    steps.append(text)
            return steps
        except Exception as e:
            logger.error(f"Error extracting instructions: {str(e)}")
            return []

    def _parse_ingredients(self, raw_ingredients: list[str]) -> list[RecipeIngredient]:
        """
        Parse raw ingredient strings into RecipeIngredient objects.

        This is a basic implementation that can be enhanced with NLP parsing
        to extract quantity, unit, and process information.
        """
        return [
            RecipeIngredient(
                name=ingredient_str,
                quantity=0.0,  # TODO: Parse from ingredient string
                unit="",  # TODO: Parse from ingredient string
                process=None,  # TODO: Parse from ingredient string
            )
            for ingredient_str in raw_ingredients
        ]

    def _parse_instructions(self, raw_instructions: list[str]) -> list[RecipeInstruction]:
        """
        Parse raw instruction strings into RecipeInstruction objects.
        """
        return [
            RecipeInstruction(
                step=step_num,
                description=instruction_str,
                list_of_ingredients_for_step=[],  # TODO: Extract ingredients used in this step
            )
            for step_num, instruction_str in enumerate(raw_instructions, start=1)
        ]
