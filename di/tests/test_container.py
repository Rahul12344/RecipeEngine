import unittest

from di import container, get_providers, provides, reset_container

# Importing these triggers their @provides registration.
from models.neer_model.neer import NEERPredictor
from models.annotation_model import RecipeAnnotationModel
from store.recipe_annotation_store import RecipeAnnotationStore
from store.recipe_user_feature_store import RecipeUserFeatureStore


class ProvidesRegistryTest(unittest.TestCase):
    def test_duplicate_registration_under_same_name_is_rejected(self):
        with self.assertRaises(ValueError):
            @provides("recipe_annotation_store")
            class Impostor:
                pass

    def test_production_classes_are_registered(self):
        providers = get_providers()
        self.assertIs(providers["recipe_annotation_store"], RecipeAnnotationStore)
        self.assertIs(providers["recipe_user_feature_store"], RecipeUserFeatureStore)
        self.assertIs(providers["neer_model"], NEERPredictor)
        self.assertIs(providers["recipe_annotation_model"], RecipeAnnotationModel)


class SingletonWiringTest(unittest.TestCase):
    def setUp(self):
        reset_container()

    def test_dependency_is_injected_by_matching_init_param_name(self):
        model = container().get(RecipeAnnotationModel)
        self.assertIsInstance(model.neer_model, NEERPredictor)

    def test_same_provider_is_reused_as_a_singleton_across_resolutions(self):
        model_one = container().get(RecipeAnnotationModel)
        model_two = container().get(RecipeAnnotationModel)
        self.assertIs(
            model_one.neer_model,
            model_two.neer_model,
            "two independently-resolved consumers must share the same singleton",
        )

    def test_singleton_is_shared_across_different_consumer_classes(self):
        class ConsumerA:
            def __init__(self, recipe_annotation_store: RecipeAnnotationStore):
                self.recipe_annotation_store = recipe_annotation_store

        class ConsumerB:
            def __init__(self, recipe_annotation_store: RecipeAnnotationStore):
                self.recipe_annotation_store = recipe_annotation_store

        a = container().get(ConsumerA)
        b = container().get(ConsumerB)
        self.assertIs(a.recipe_annotation_store, b.recipe_annotation_store)

    def test_unregistered_param_name_is_not_auto_wired(self):
        class NotAProvider:
            pass

        class Consumer:
            def __init__(self, not_a_provider: NotAProvider):
                self.not_a_provider = not_a_provider

        with self.assertRaises(Exception):
            container().get(Consumer)


if __name__ == "__main__":
    unittest.main()
