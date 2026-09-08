"""Persistence for a user's ingredient inventory.

This class has no Postgres-specific code at all, and doesn't even depend on
Postgres being the backing technology: it's injected (via DI) with anything
conforming to the generic AsyncKVStore[str, UserIngredientInventory]
interface (async_store/async_kv_store.py) and just delegates through
get/set. This store has no extra indexed columns, so the plain AsyncKVStore
contract is all it needs -- unlike RecipeStore/RecipeAnnotationStore, it
doesn't require IndexedPostgresStore's richer get_by_column/list. That
means whatever's registered for "user_ingredient_inventory_backing_store"
can be swapped between IndexedPostgresStore (see
store/postgres/user_ingredient_inventory_backing_store.py) and an
InMemoryKVStore (async_store/in_memory_kv_store.py) purely via DI, with
zero changes here.
"""
from __future__ import annotations

from async_store.async_kv_store import AsyncKVStore
from di import provides
from models.features.unit_conversion import convert_quantity
from models.features.user_ingredient_inventory import ConsumeIngredientsResult, InventoryItem, UserIngredientInventory
from models.output_data_models.annotation_model_features import RecipeIngredient
from recommender.ingredient_matching import ingredients_match


@provides("user_ingredient_inventory_store")
class UserIngredientInventoryStore:
    """Get/set a user's full ingredient inventory, and add/remove individual items. No SQL/Postgres details here."""

    def __init__(self, user_ingredient_inventory_backing_store: AsyncKVStore):
        self._backing_store = user_ingredient_inventory_backing_store

    async def get_inventory(self, user_id: str) -> UserIngredientInventory:
        """Return the user's inventory, or an empty one if none is stored."""
        inventory = await self._backing_store.get(user_id)
        return inventory if inventory is not None else UserIngredientInventory(user_id=user_id, items=[])

    async def set_inventory(self, inventory: UserIngredientInventory) -> None:
        """Overwrite the user's entire inventory."""
        await self._backing_store.set(inventory.user_id, inventory)

    async def add_item(self, user_id: str, item: InventoryItem) -> UserIngredientInventory:
        """Add (or replace, by name) a single item in the user's inventory."""
        inventory = await self.get_inventory(user_id)
        remaining = [existing for existing in inventory.items if existing.name.lower() != item.name.lower()]
        remaining.append(item)
        updated = UserIngredientInventory(user_id=user_id, items=remaining)
        await self.set_inventory(updated)
        return updated

    async def remove_item(self, user_id: str, item_name: str) -> UserIngredientInventory:
        """Remove a single item (matched case-insensitively by name) from the user's inventory."""
        inventory = await self.get_inventory(user_id)
        remaining = [existing for existing in inventory.items if existing.name.lower() != item_name.lower()]
        updated = UserIngredientInventory(user_id=user_id, items=remaining)
        await self.set_inventory(updated)
        return updated

    async def restock_item(self, user_id: str, item: InventoryItem) -> UserIngredientInventory:
        """Add stock for `item`, netting against any existing (possibly
        negative) quantity for an item with the same name.

        Unlike add_item (which replaces the matching item outright), this
        sums quantities so that a prior deficit -- e.g. left over from
        consume_ingredients running short -- is paid down by the new stock
        instead of being silently overwritten. Falls back to add_item's
        replace behavior if there's no existing item to merge with, or if
        the two items' units can't be reconciled via unit conversion.
        """
        inventory = await self.get_inventory(user_id)
        existing = next((i for i in inventory.items if i.name.lower() == item.name.lower()), None)

        converted = None
        if (
            existing is not None
            and existing.quantity is not None
            and existing.unit is not None
            and item.quantity is not None
            and item.unit is not None
        ):
            converted = convert_quantity(item.quantity, item.unit, existing.unit, ingredient_name=item.name)

        if existing is None or converted is None:
            return await self.add_item(user_id, item)

        merged = InventoryItem(name=existing.name, quantity=existing.quantity + converted, unit=existing.unit)
        return await self.add_item(user_id, merged)

    async def consume_ingredients(
        self, user_id: str, ingredients: list[RecipeIngredient]
    ) -> ConsumeIngredientsResult:
        """Deduct a recipe's ingredient quantities from a user's inventory.

        Each ingredient is matched to an inventory item by fuzzy name
        (ingredients_match). A recipe ingredient with no matching inventory
        item creates a new item with a negative quantity -- a deficit that
        restock_item will pay down later. Insufficient stock is allowed to
        go negative rather than clamped or blocked. A match whose unit can't
        be reconciled via unit conversion is left untouched and its name is
        reported in the result's unresolved_ingredients.
        """
        inventory = await self.get_inventory(user_id)
        items = list(inventory.items)
        unresolved: list[str] = []

        for ingredient in ingredients:
            match_index = next(
                (i for i, existing in enumerate(items) if ingredients_match(existing.name, ingredient.name)),
                None,
            )

            if match_index is None:
                items.append(InventoryItem(name=ingredient.name, quantity=-ingredient.quantity, unit=ingredient.unit))
                continue

            existing = items[match_index]
            if existing.quantity is None or existing.unit is None:
                unresolved.append(ingredient.name)
                continue

            converted = convert_quantity(
                ingredient.quantity, ingredient.unit, existing.unit, ingredient_name=ingredient.name
            )
            if converted is None:
                unresolved.append(ingredient.name)
                continue

            items[match_index] = InventoryItem(
                name=existing.name, quantity=existing.quantity - converted, unit=existing.unit
            )

        updated = UserIngredientInventory(user_id=user_id, items=items)
        await self.set_inventory(updated)
        return ConsumeIngredientsResult(updated_inventory=updated, unresolved_ingredients=unresolved)

    async def close(self) -> None:
        await self._backing_store.close()
