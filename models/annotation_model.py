from di import provides


@provides("recipe_annotation_model")
class RecipeAnnotationModel:
    def __init__(self, neer_model):
        self.neer_model = neer_model

    def annotate(self, recipe_text: str) -> str:
        return self.neer_model(recipe_text)
