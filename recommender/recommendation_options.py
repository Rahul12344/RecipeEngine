from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationOptions:
    """Knobs a caller can set for a single recommendation request."""

    # Maximum number of recipes to return. `None` means "no limit".
    limit: int | None = None

    # Drop recipes whose inventory match ratio is below this threshold
    # (0.0 means "no filtering, just rank everything").
    min_match_ratio: float = 0.0
