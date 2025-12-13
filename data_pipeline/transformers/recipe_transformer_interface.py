from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from models.output_data_models.annotation_model_features import Recipe


class RecipeTransformerInterface(ABC):
    """
    Interface for transforming raw HTML from recipe sources into Recipe data models.
    """

    @abstractmethod
    def transform(self, html: str, url: str) -> Recipe | None:
        """
        Transform raw HTML into a Recipe data model.

        Args:
            html: Raw HTML content from the recipe source
            url: URL of the recipe page

        Returns:
            Recipe object if transformation is successful, None otherwise
        """
        raise NotImplementedError("Subclasses must implement transform method")

    @abstractmethod
    def is_recipe_page(self, html: str) -> bool:
        """
        Check if the HTML content represents a recipe page.

        Args:
            html: Raw HTML content to check

        Returns:
            True if the page is a recipe page, False otherwise
        """
        raise NotImplementedError("Subclasses must implement is_recipe_page method")

