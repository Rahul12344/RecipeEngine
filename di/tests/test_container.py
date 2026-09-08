import unittest

from di import container, get_providers, provides, reset_container

# Importing these triggers their @provides registration.
from models.neer_model.neer import NEERPredictor
from models.annotation_model import RecipeAnnotationModel
from store.postgres.recipe_annotation_backing_store import build_recipe_annotation_backing_store  # noqa: F401
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


class FunctionProviderTest(unittest.TestCase):
    """@provides also accepts a zero-arg function, not just a class -- for
    building a singleton whose construction needs logic beyond a class's own
    __init__ (e.g. a generically-configured instance of a shared class)."""

    def setUp(self):
        reset_container()

    def test_function_provider_is_registered_and_not_a_class(self):
        @provides("test_widget_from_function")
        def build_widget():
            return {"built": True}

        providers = get_providers()
        self.assertIn("test_widget_from_function", providers)
        self.assertFalse(hasattr(providers["test_widget_from_function"], "__di_name__"))

    def test_function_provider_result_is_injected_by_matching_param_name(self):
        @provides("test_widget_a")
        def build_widget():
            return {"built": True}

        class Consumer:
            def __init__(self, test_widget_a):
                self.widget = test_widget_a

        consumer = container().get(Consumer)
        self.assertEqual(consumer.widget, {"built": True})

    def test_function_provider_is_called_once_and_memoized_as_a_singleton(self):
        call_count = 0

        @provides("test_widget_b")
        def build_widget():
            nonlocal call_count
            call_count += 1
            return object()

        class ConsumerA:
            def __init__(self, test_widget_b):
                self.widget = test_widget_b

        class ConsumerB:
            def __init__(self, test_widget_b):
                self.widget = test_widget_b

        a = container().get(ConsumerA)
        b = container().get(ConsumerB)
        self.assertIs(a.widget, b.widget)
        self.assertEqual(call_count, 1)

    def test_class_and_function_providers_can_be_mixed_in_one_consumer(self):
        @provides("test_widget_c")
        def build_widget():
            return "from a function"

        class Consumer:
            def __init__(self, test_widget_c, recipe_annotation_store: RecipeAnnotationStore):
                self.widget = test_widget_c
                self.store = recipe_annotation_store

        consumer = container().get(Consumer)
        self.assertEqual(consumer.widget, "from a function")
        self.assertIsInstance(consumer.store, RecipeAnnotationStore)

    def test_function_provider_params_are_injected_by_name_like_a_class_init(self):
        """A provider function's own parameters are injectable, exactly like
        a class's __init__ params -- so one provider can be built on top of
        another without calling it directly."""

        @provides("test_leaf_value")
        def provide_leaf():
            return "leaf-value"

        @provides("test_composed_widget")
        def build_widget(test_leaf_value):
            return f"built-from-{test_leaf_value}"

        class Consumer:
            def __init__(self, test_composed_widget):
                self.widget = test_composed_widget

        consumer = container().get(Consumer)
        self.assertEqual(consumer.widget, "built-from-leaf-value")

    def test_function_provider_with_missing_dependency_raises_cleanly(self):
        """A provider function depending on an unregistered name fails with
        a clear pinject error, not an internal crash from the dynamically
        built wrapper (verified directly against pinject before relying on
        this in di/container.py)."""

        @provides("test_widget_with_missing_dep")
        def build_widget(test_nonexistent_dependency):
            return test_nonexistent_dependency

        class Consumer:
            def __init__(self, test_widget_with_missing_dep):
                self.widget = test_widget_with_missing_dep

        with self.assertRaises(Exception):
            container().get(Consumer)

    def test_provider_returning_none_is_injected_without_crashing(self):
        """A provider legitimately resolving to None (e.g. an env-var-backed
        value that isn't set) must be injectable without pinject's own
        rejection-error formatting crashing on this module's exec-generated
        provider wrappers -- this is a real bug this project hit: a config
        value provider returning None during a nested provider function's
        own dependency injection crashed instead of just passing None
        through, so the consumer could handle it. Regression test for
        allow_injecting_none in di/container.py."""

        @provides("test_optional_value")
        def build_optional_value():
            return None

        @provides("test_widget_depending_on_optional")
        def build_widget(test_optional_value):
            return f"got-{test_optional_value}"

        class Consumer:
            def __init__(self, test_widget_depending_on_optional):
                self.widget = test_widget_depending_on_optional

        consumer = container().get(Consumer)
        self.assertEqual(consumer.widget, "got-None")


if __name__ == "__main__":
    unittest.main()
