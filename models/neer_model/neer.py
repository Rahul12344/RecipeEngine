from __future__ import annotations

from di import provides


@provides("neer_model")
class NEERPredictor:
    def __call__(
        self,
        features: NEERFeatures
    ) -> RecipeEntity:
        pass