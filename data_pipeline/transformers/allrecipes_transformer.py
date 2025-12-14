from bs4 import BeautifulSoup
import logging
from typing import Optional
from transformers.recipe_transformer_interface import RecipeTransformerInterface
from models.output_data_models.annotation_model_features import (
    Recipe,
    RecipeIngredient,
    RecipeInstruction
)

logger = logging.getLogger(__name__)


class AllRecipesTransformer(RecipeTransformerInterface):
    """
    Transformer for extracting recipe data from AllRecipes.com HTML.
    """

    def transform(self, html: str, url: str) -> Optional[Recipe]:
        """
        Transform AllRecipes HTML into a Recipe data model.

        Args:
            html: Raw HTML content from AllRecipes
            url: URL of the recipe page

        Returns:
            Recipe object if transformation is successful, None otherwise
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract recipe name
            name = self._get_name(soup)
            if not name:
                logger.warning(f"Could not extract recipe name from {url}")
                return None

            # Extract ingredients
            ingredients = self._get_ingredients(soup)

            # Extract instructions/steps
            instructions = self._get_instructions(soup)

            # Convert raw ingredient strings to RecipeIngredient objects
            recipe_ingredients = self._parse_ingredients(ingredients)

            # Convert raw step strings to RecipeInstruction objects
            recipe_instructions = self._parse_instructions(instructions, recipe_ingredients)

            logger.debug(f"Successfully transformed recipe: {name}")

            return Recipe(
                name=name,
                total_ingredients=recipe_ingredients,
                instructions=recipe_instructions
            )

        except Exception as e:
            logger.error(f"Error transforming recipe from {url}: {str(e)}", exc_info=True)
            return None

    def is_recipe_page(self, html: str) -> bool:
        """
        Check if the HTML content represents an AllRecipes recipe page.

        Args:
            html: Raw HTML content to check

        Returns:
            True if the page is a recipe page, False otherwise
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            is_recipe = bool(soup.find('div', class_='recipe-container'))
            logger.debug(f"Page is recipe: {is_recipe}")
            return is_recipe
        except Exception as e:
            logger.error(f"Error checking if page is recipe: {str(e)}")
            return False

    def _get_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract recipe name from the page"""
        try:
            element = soup.find("h1", {"id": "article-heading_2-0"})
            return element.get_text().strip(' \t\n\r') if element else None
        except Exception as e:
            logger.error(f"Error extracting name: {str(e)}")
            return None

    def _get_ingredients(self, soup: BeautifulSoup) -> list[str]:
        """Extract raw ingredient strings from the page"""
        try:
            ingredients_div = soup.find("div", {"id": "mntl-structured-ingredients_1-0"})
            if not ingredients_div:
                return []
            return [li.get_text().strip(' \t\n\r') for li in ingredients_div.find_all("li")]
        except Exception as e:
            logger.error(f"Error extracting ingredients: {str(e)}")
            return []

    def _get_instructions(self, soup: BeautifulSoup) -> list[str]:
        """Extract raw instruction strings from the page"""
        try:
            steps_div = soup.find("div", {"id": "recipe__steps_1-0"})
            if not steps_div:
                return []
            return [li.get_text().strip(' \t\n\r') for li in steps_div.find_all("li")]
        except Exception as e:
            logger.error(f"Error extracting instructions: {str(e)}")
            return []

    def _parse_ingredients(self, raw_ingredients: list[str]) -> list[RecipeIngredient]:
        """
        Parse raw ingredient strings into RecipeIngredient objects.

        This is a basic implementation that can be enhanced with NLP parsing
        to extract quantity, unit, and process information.
        """
        recipe_ingredients = []
        for ingredient_str in raw_ingredients:
            # Basic parsing - can be enhanced with more sophisticated NLP
            # For now, we'll create a simple RecipeIngredient with the full string as name
            recipe_ingredients.append(
                RecipeIngredient(
                    name=ingredient_str,
                    quantity=0.0,  # TODO: Parse from ingredient string
                    unit="",  # TODO: Parse from ingredient string
                    process=None  # TODO: Parse from ingredient string
                )
            )
        return recipe_ingredients

    def _parse_instructions(self, raw_instructions: list[str], ingredients: list[RecipeIngredient]) -> list[RecipeInstruction]:
        """
        Parse raw instruction strings into RecipeInstruction objects.

        Args:
            raw_instructions: List of instruction strings
            ingredients: List of RecipeIngredient objects for reference

        Returns:
            List of RecipeInstruction objects
        """
        recipe_instructions = []
        for step_num, instruction_str in enumerate(raw_instructions, start=1):
            # For now, we'll create instructions without ingredient references
            # This can be enhanced with NLP to identify which ingredients are used in each step
            recipe_instructions.append(
                RecipeInstruction(
                    step=step_num,
                    description=instruction_str,
                    list_of_ingredients_for_step=[]  # TODO: Extract ingredients used in this step
                )
            )
        return recipe_instructions

