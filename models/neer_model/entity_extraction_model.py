import torch

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

class EntityExtractionModel:
    def __call__(
        self,
        features: NEERFeatures
    ) -> List[RecipeEntity]:
        pass
