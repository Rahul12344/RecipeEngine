from dataclasses import dataclass
from enum import Enum

class Vegetarian(Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non-vegetarian"
    VEGAN = "vegan"


@dataclass(frozen=True)
class RecipeIngredient:
    name: str
    quantity: float
    unit: str

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
    time: str
    difficulty: str
    cost: str

@dataclass(frozen=True)
class RecipeMetadata:
    vegetarian: Vegetarian
    group: str
    effort: Effort

@dataclass(frozen=True)
class RecipeAnnotation:
    recipe: Recipe
    recipe_metadata: RecipeMetadata
