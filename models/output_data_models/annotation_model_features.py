from dataclasses import dataclass
from enum import Enum

class Diet(Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non-vegetarian"
    PESCATARIAN = "pescatarian"
    VEGAN = "vegan"

class DietTag(Enum):
    KETO = "keto"
    GLUTEN_FREE = "gluten-free"
    LACTOSE_FREE = "lactose-free"
    PALEO = "paleo"
    MEDITERRANEAN = "mediterranean"
    HALAL = "halal"
    KOSHER = "kosher"
    NUT_FREE = "nut-free"
    SEAFOOD_FREE = "seafood-free"
    SOY_FREE = "soy-free"
    WHEAT_FREE = "wheat-free"
    PEANUT_FREE = "peanut-free"


@dataclass(frozen=True)
class RecipeIngredient:
    name: str
    quantity: float
    unit: str
    process: str | None = None

@dataclass(frozen=True)
class RecipeInstruction:
    step: int
    description: str
    list_of_ingredients_for_step: list[RecipeIngredient]

@dataclass(frozen=True)
class Recipe:
    name: str
    total_ingredients: list[RecipeIngredient]
    instructions: list[RecipeInstruction]

@dataclass(frozen=True)
class Effort:
    cook_time: str
    prep_time: str
    difficulty: str
    cost: str

@dataclass(frozen=True)
class Nutrition:
    calories: int
    protein: int
    carbs: int
    fat: int
    saturated_fat: int
    cholesterol: int
    sodium: int
    fiber: int
    sugar: int

@dataclass(frozen=True)
class RecipeMetadata:
    diet: Diet
    group: str
    effort: Effort
    diet_tags: list[DietTag]

@dataclass(frozen=True)
class RecipeAnnotation:
    recipe: Recipe
    recipe_metadata: RecipeMetadata
