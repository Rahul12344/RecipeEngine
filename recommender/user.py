from __future__ import annotations

from dataclasses import dataclass

from models.features.user_ingredient_inventory import UserIngredientInventory


@dataclass(frozen=True)
class User:
    """The subject of a recommendation request.

    `inventory` is the user's already-resolved ingredient inventory (e.g.
    fetched from `UserIngredientInventoryStore` ahead of time by the
    caller). Keeping it as plain data here -- rather than having `User`
    reach into a store itself -- keeps the recommendation pipeline
    synchronous and trivially testable without a database.
    """

    user_id: str
    inventory: UserIngredientInventory

    def get_inventory(self) -> UserIngredientInventory:
        """The user's way to reach their ingredient inventory."""
        return self.inventory
