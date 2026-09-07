"""
Tests for config/database.py's provide_database_url.
"""
import unittest
from unittest import mock

from config import env
from config.database import DATABASE_URL_ENV_VAR, provide_database_url
from di import container, reset_container


class ProvideDatabaseUrlTest(unittest.TestCase):
    def setUp(self):
        env._dotenv_values.cache_clear()
        self.addCleanup(env._dotenv_values.cache_clear)

    def test_reads_the_expected_env_var_name(self):
        self.assertEqual(DATABASE_URL_ENV_VAR, "RECIPE_ENGINE_DATABASE_URL")

    def test_returns_the_configured_value(self):
        with mock.patch.dict("os.environ", {"RECIPE_ENGINE_DATABASE_URL": "postgresql://x/y"}):
            self.assertEqual(provide_database_url(), "postgresql://x/y")

    def test_returns_none_when_unconfigured(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(provide_database_url())

    def test_is_directly_callable_as_a_plain_function(self):
        """@provides doesn't wrap its target -- provide_database_url stays a
        normal function other code can call directly, not just resolve
        through DI."""
        self.assertTrue(callable(provide_database_url))
        self.assertFalse(hasattr(provide_database_url, "__di_name__"))


class DatabaseUrlInjectionTest(unittest.TestCase):
    """Confirms provide_database_url is actually registered with DI (not
    just directly callable) -- see store/postgres/*_backing_store.py for the
    real consumers that inject it by name."""

    def setUp(self):
        env._dotenv_values.cache_clear()
        self.addCleanup(env._dotenv_values.cache_clear)
        reset_container()
        self.addCleanup(reset_container)

    def test_database_url_is_injectable_by_name(self):
        class Consumer:
            def __init__(self, database_url):
                self.database_url = database_url

        with mock.patch.dict("os.environ", {"RECIPE_ENGINE_DATABASE_URL": "postgresql://x/y"}):
            reset_container()
            consumer = container().get(Consumer)
        self.assertEqual(consumer.database_url, "postgresql://x/y")


if __name__ == "__main__":
    unittest.main()
