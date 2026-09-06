from __future__ import annotations

import torch


class EntityExtractionModel:
    def __call__(
        self,
        features: NEERFeatures
    ) -> List[RecipeEntity]:
        pass

class ViterbiCRFModel(EntityExtractionModel, torch.nn.Module):
    pass

class DiffusionNERModel(EntityExtractionModel, torch.nn.Module):
    # Implementation of https://github.com/tricktreat/DiffusionNER/tree/main
    def __call__(
        self,
        features: NEERFeatures
    ) -> List[RecipeEntity]:
        pass

    def forward(self):
        pass
