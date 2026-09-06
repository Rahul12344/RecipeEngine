from dataclasses import dataclass, field


@dataclass(frozen=True)
class InventoryItem:
    """A single ingredient a user currently has on hand."""

    name: str
    quantity: float | None = None
    unit: str | None = None


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
