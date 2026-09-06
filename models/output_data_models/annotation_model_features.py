from __future__ import annotations

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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "process": self.process,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RecipeIngredient:
        return cls(
            name=data["name"],
            quantity=data["quantity"],
            unit=data["unit"],
            process=data.get("process"),
        )

@dataclass(frozen=True)
class RecipeInstruction:
    step: int
    description: str
    list_of_ingredients_for_step: list[RecipeIngredient]

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "description": self.description,
            "list_of_ingredients_for_step": [i.to_dict() for i in self.list_of_ingredients_for_step],
        }

    @classmethod
    def from_dict(cls, data: dict) -> RecipeInstruction:
        return cls(
            step=data["step"],
            description=data["description"],
            list_of_ingredients_for_step=[
                RecipeIngredient.from_dict(i) for i in data.get("list_of_ingredients_for_step", [])
            ],
        )

@dataclass(frozen=True)
class Recipe:
    name: str
    total_ingredients: list[RecipeIngredient]
    instructions: list[RecipeInstruction]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_ingredients": [i.to_dict() for i in self.total_ingredients],
            "instructions": [i.to_dict() for i in self.instructions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Recipe:
        return cls(
            name=data["name"],
            total_ingredients=[RecipeIngredient.from_dict(i) for i in data.get("total_ingredients", [])],
            instructions=[RecipeInstruction.from_dict(i) for i in data.get("instructions", [])],
        )

@dataclass(frozen=True)
class Effort:
    cook_time: str
    prep_time: str
    difficulty: str
    cost: str

    def to_dict(self) -> dict:
        return {
            "cook_time": self.cook_time,
            "prep_time": self.prep_time,
            "difficulty": self.difficulty,
            "cost": self.cost,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Effort:
        return cls(
            cook_time=data["cook_time"],
            prep_time=data["prep_time"],
            difficulty=data["difficulty"],
            cost=data["cost"],
        )

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

    def to_dict(self) -> dict:
        return {
            "diet": self.diet.value,
            "group": self.group,
            "effort": self.effort.to_dict(),
            "diet_tags": [tag.value for tag in self.diet_tags],
        }

    @classmethod
    def from_dict(cls, data: dict) -> RecipeMetadata:
        return cls(
            diet=Diet(data["diet"]),
            group=data["group"],
            effort=Effort.from_dict(data["effort"]),
            diet_tags=[DietTag(tag) for tag in data.get("diet_tags", [])],
        )

@dataclass(frozen=True)
class RecipeAnnotation:
    recipe: Recipe
    recipe_metadata: RecipeMetadata

    def to_dict(self) -> dict:
        return {
            "recipe": self.recipe.to_dict(),
            "recipe_metadata": self.recipe_metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> RecipeAnnotation:
        return cls(
            recipe=Recipe.from_dict(data["recipe"]),
            recipe_metadata=RecipeMetadata.from_dict(data["recipe_metadata"]),
        )
