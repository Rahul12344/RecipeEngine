"""Unit conversion for ingredient quantities.

Bridges the free-text unit strings used by `InventoryItem`
(models/features/user_ingredient_inventory.py) and `RecipeIngredient`
(models/output_data_models/annotation_model_features.py) so that quantities
expressed in different units (e.g. recipe wants "2 cup flour", inventory
tracks "500 g flour") can be compared and combined.

Same-dimension conversions (mass<->mass, volume<->volume, count<->count) are
exact factor math. Cross-dimension conversions (mass<->volume) require an
ingredient-specific density and are only possible for the small, manually
curated set of ingredients in `INGREDIENT_DENSITY_G_PER_ML`. Anything else --
an unrecognized unit, or a cross-dimension conversion with no known density --
returns None; callers must treat that as "cannot reconcile these units".
"""
from __future__ import annotations

import re
from enum import Enum


class UnitDimension(Enum):
    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"


# Normalized unit name -> (dimension, factor to convert 1 of that unit into
# the dimension's base unit). Base units: grams (MASS), milliliters (VOLUME),
# each (COUNT).
UNIT_TO_BASE: dict[str, tuple[UnitDimension, float]] = {
    "g": (UnitDimension.MASS, 1.0),
    "gram": (UnitDimension.MASS, 1.0),
    "kg": (UnitDimension.MASS, 1000.0),
    "oz": (UnitDimension.MASS, 28.3495),
    "lb": (UnitDimension.MASS, 453.592),
    "ml": (UnitDimension.VOLUME, 1.0),
    "l": (UnitDimension.VOLUME, 1000.0),
    "cup": (UnitDimension.VOLUME, 236.588),
    "tbsp": (UnitDimension.VOLUME, 14.7868),
    "tsp": (UnitDimension.VOLUME, 4.92892),
    "fl oz": (UnitDimension.VOLUME, 29.5735),
    "pint": (UnitDimension.VOLUME, 473.176),
    "quart": (UnitDimension.VOLUME, 946.353),
    "gallon": (UnitDimension.VOLUME, 3785.41),
    "each": (UnitDimension.COUNT, 1.0),
    "count": (UnitDimension.COUNT, 1.0),
    "unit": (UnitDimension.COUNT, 1.0),
    "clove": (UnitDimension.COUNT, 1.0),
    "slice": (UnitDimension.COUNT, 1.0),
    "whole": (UnitDimension.COUNT, 1.0),
}

# Approximate grams-per-milliliter density for a small, manually curated set
# of common cooking ingredients, used only to bridge MASS <-> VOLUME
# conversions. Not a general food-density database: an ingredient not listed
# here simply can't be converted across dimensions.
INGREDIENT_DENSITY_G_PER_ML: dict[str, float] = {
    "water": 1.0,
    "milk": 1.03,
    "flour": 0.507,
    "all purpose flour": 0.507,
    "sugar": 0.845,
    "granulated sugar": 0.845,
    "butter": 0.959,
    "oil": 0.92,
    "vegetable oil": 0.92,
    "olive oil": 0.92,
    "rice": 0.85,
    "salt": 1.2,
}

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_unit(text: str) -> str:
    """Lowercase and collapse punctuation/whitespace for table lookups.

    Used for both unit strings ("Fl-Oz" -> "fl oz") and ingredient names
    ("All-Purpose Flour" -> "all purpose flour") since both are matched
    against exact-key dictionaries above.
    """
    return _NORMALIZE_RE.sub(" ", text.strip().lower()).strip()


def convert_quantity(
    quantity: float,
    from_unit: str,
    to_unit: str,
    *,
    ingredient_name: str | None = None,
) -> float | None:
    """Convert `quantity` of `from_unit` into `to_unit`.

    Returns None if either unit is unrecognized, or if the two units are in
    different dimensions (mass vs. volume) and no density is known for
    `ingredient_name`. Count can't be bridged to mass/volume at all (that
    would require ingredient-specific unit weights, e.g. "1 egg" ~= 50g,
    which this module doesn't model).
    """
    from_key = normalize_unit(from_unit)
    to_key = normalize_unit(to_unit)
    if from_key == to_key:
        return quantity

    from_entry = UNIT_TO_BASE.get(from_key)
    to_entry = UNIT_TO_BASE.get(to_key)
    if from_entry is None or to_entry is None:
        return None

    from_dimension, from_factor = from_entry
    to_dimension, to_factor = to_entry
    base_quantity = quantity * from_factor

    if from_dimension == to_dimension:
        return base_quantity / to_factor

    if from_dimension == UnitDimension.COUNT or to_dimension == UnitDimension.COUNT:
        return None

    density = _lookup_density(ingredient_name)
    if density is None:
        return None

    if from_dimension == UnitDimension.MASS:
        # base_quantity is grams; convert to ml via density, then to to_unit.
        return (base_quantity / density) / to_factor
    else:
        # base_quantity is ml; convert to grams via density, then to to_unit.
        return (base_quantity * density) / to_factor


def _lookup_density(ingredient_name: str | None) -> float | None:
    if not ingredient_name:
        return None
    return INGREDIENT_DENSITY_G_PER_ML.get(normalize_unit(ingredient_name))
