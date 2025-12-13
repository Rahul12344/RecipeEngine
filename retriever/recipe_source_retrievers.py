from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen, Request
import ssl
import re
import time
import random
import logging
from typing import List, Dict, Set

# TODO: Rethink logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecipeSourceRetrieverInterface:
    def get_recipe_from_url(self, url: str) -> list[dict]:
        raise NotImplementedError("Subclasses must implement get_recipe_from_url method")

    def get_all_recipes(self) -> list[dict]:
        raise NotImplementedError("Subclasses must implement get_all_recipes method")

class AllRecipesSourceRetriever(RecipeSourceRetrieverInterface):
    """
    Scrape recipes from allrecipes.com
    """
    def __init__(self, base_url: str = "https://www.allrecipes.com"):
        self._base_url = base_url
        self._visited_urls: Set[str] = set()
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': ''
        }
        # Create SSL context to handle HTTPS
        self._ssl_context = ssl._create_unverified_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE
        logger.info(f"Initialized AllRecipesSourceRetriever with base URL: {base_url}")

    def get_recipe_from_url(self, url: str) -> list[dict]:
        """Scrape a single recipe from a given URL"""
        logger.info(f"Scraping recipe from URL: {url}")
        recipes = []
        self._scrape_recipes(url, recipes)
        logger.info(f"Completed scraping. Found {len(recipes)} recipes")
        return recipes

    def get_all_recipes(self) -> list[dict]:
        """Scrape recipes from allrecipes.com recursively"""
        logger.info("Starting recipe scraping process")
        recipes = []
        self._scrape_recipes(self._base_url, recipes)
        logger.info(f"Completed scraping. Found {len(self._recipes)} recipes")
        return {"recipes": recipes}

    def _scrape_recipes(self, url: str, recipes: list[dict] = []) -> None:
        """Recursively scrape recipes from the given URL"""
        if url in self._visited_urls:
            return

        self._visited_urls.add(url)
        logger.info(f"Scraping URL: {url}")

        try:
            req = Request(url, headers=self._headers)
            with urlopen(req, context=self._ssl_context) as response:
                html = response.read()
                soup = BeautifulSoup(html, 'html.parser')

                # Check if this is a recipe page
                if self._is_recipe_page(soup):
                    recipe_data = self._extract_recipe_data(soup, url)
                    if recipe_data:
                        recipes.append(recipe_data)
                        logger.debug(f"Successfully extracted recipe: {recipe_data['name']}")

                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/recipe/') or href.startswith('/recipes/'):
                        full_url = urljoin(self._base_url, href)
                        if full_url not in self._visited_urls:
                            time.sleep(random.uniform(1, 3))
                            self._scrape_recipes(full_url, recipes)

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}", exc_info=True)

    def _is_recipe_page(self, soup: BeautifulSoup) -> bool:
        """Check if the current page is a recipe page"""
        is_recipe = bool(soup.find('div', class_='recipe-container'))
        logger.debug(f"Page is recipe: {is_recipe}")
        return is_recipe

    def _extract_recipe_data(self, soup: BeautifulSoup, url: str) -> dict:
        """Extract recipe data from the page"""
        try:
            # Extract recipe name
            name = self._get_name(soup)
            rating = self._get_rating(soup)
            ingredients = self._get_ingredients(soup)
            steps = self._get_steps(soup)
            prep_time = self._get_prep_time(soup)
            cook_time = self._get_cook_time(soup)
            total_time = self._get_total_time(soup)
            nb_servings = self._get_nb_servings(soup)

            logger.debug(f"Successfully extracted recipe data for: {name}")

            recipe_data = {
                "name": name,
                "rating": rating,
                "ingredients": ingredients,
                "steps": steps,
                "prep_time": prep_time,
                "cook_time": cook_time,
                "total_time": total_time,
                "nb_servings": nb_servings,
            }

            return recipe_data

        except Exception as e:
            logger.error(f"Error extracting recipe data: {str(e)}", exc_info=True)
            return None

	def _get_name(self, soup):
		return soup.find("h1", {"id": "article-heading_2-0"}).get_text().strip(' \t\n\r')

	def _get_rating(self, soup):
		return float(soup.find("div", {"id": "mntl-recipe-review-bar__rating_2-0"}).get_text().strip(' \t\n\r'))

	def _get_ingredients(self, soup):
		return [li.get_text().strip(' \t\n\r') for li in soup.find("div", {"id": "mntl-structured-ingredients_1-0"}).find_all("li")]

	def _get_steps(self, soup):
		return [li.get_text().strip(' \t\n\r') for li in soup.find("div", {"id": "recipe__steps_1-0"}).find_all("li")]

	def _get_times_data(self, text):
		return soup.find("div", {"id": "recipe-details_1-0"}).find("div", text=text).parent.find("div", {"class": "mntl-recipe-details__value"}).get_text().strip(' \t\n\r')

	def _get_prep_time(self, soup):
		return self._get_times_data(soup, "Prep Time:")

	def _get_cook_time(self, soup):
		return self._get_times_data(soup, "Cook Time:")

	def _get_total_time(self, soup):
		return self._get_times_data(soup, "Total Time:")

	def _get_nb_servings(self, soup):
		return self._get_times_data(soup, "Servings:")

class FoodNetworkSourceRetriever(RecipeSourceRetrieverInterface):
    def get_recipe_from_url(self, url: str) -> list[dict]:
        pass

    def get_all_recipes(self) -> list[dict]:
        pass