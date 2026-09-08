from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InventoryItem:
    """A single ingredient a user currently has on hand."""

    name: str
    quantity: float | None = None
    unit: str | None = None

    def to_dict(self) -> dict:
        return {"name": self.name, "quantity": self.quantity, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict) -> InventoryItem:
        return cls(name=data["name"], quantity=data.get("quantity"), unit=data.get("unit"))


@dataclass(frozen=True)
class UserIngredientInventory:
    """The full set of ingredients a given user currently has on hand.

    This is distinct from `UserFeatures` (models/features/user_features.py),
    which tracks per-(user, recipe) engagement (ratings, views, cooks, saves).
    An inventory has no notion of a specific recipe; it's simply what
    ingredients are available to the user right now.
    """

    user_id: str
    items: list[InventoryItem] = field(default_factory=list)


@dataclass(frozen=True)
class ConsumeIngredientsResult:
    """Result of deducting a recipe's ingredients from a user's inventory.

    `unresolved_ingredients` lists ingredient names whose unit couldn't be
    reconciled with the matching inventory item's unit; those items were
    left untouched in `updated_inventory`.
    """

    updated_inventory: UserIngredientInventory
    unresolved_ingredients: list[str]
