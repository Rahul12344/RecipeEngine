"""
Tests for config/env.py's read_env_var: the generic boilerplate every
env-var-backed config provider (e.g. config/database.py) is built on.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from config import env


class ReadEnvVarTest(unittest.TestCase):
    def setUp(self):
        # _dotenv_values() is @lru_cache'd (the file is only meant to be
        # parsed once per process); clear it and point at a fresh temp file
        # per test so tests don't leak dotenv state into each other.
        env._dotenv_values.cache_clear()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._env_file = Path(self._tmpdir.name) / ".env"
        self._path_patcher = mock.patch.object(env, "_ENV_FILE_PATH", self._env_file)
        self._path_patcher.start()
        self.addCleanup(self._path_patcher.stop)
        self.addCleanup(env._dotenv_values.cache_clear)

    def test_missing_dotenv_file_and_missing_real_env_returns_none(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(env.read_env_var("SOME_VAR"))

    def test_falls_back_to_dotenv_when_real_env_is_unset(self):
        self._env_file.write_text("SOME_VAR=from-dotenv\n")
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(env.read_env_var("SOME_VAR"), "from-dotenv")

    def test_real_env_takes_precedence_over_dotenv(self):
        self._env_file.write_text("SOME_VAR=from-dotenv\n")
        with mock.patch.dict("os.environ", {"SOME_VAR": "from-real-env"}):
            self.assertEqual(env.read_env_var("SOME_VAR"), "from-real-env")

    def test_dotenv_parsing_skips_blank_lines_and_comments(self):
        self._env_file.write_text("\n# a comment\nSOME_VAR=value\n\n# trailing comment\n")
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(env.read_env_var("SOME_VAR"), "value")

    def test_dotenv_parsing_strips_surrounding_quotes(self):
        self._env_file.write_text('SOME_VAR="quoted-value"\nOTHER_VAR=\'single-quoted\'\n')
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(env.read_env_var("SOME_VAR"), "quoted-value")
            self.assertEqual(env.read_env_var("OTHER_VAR"), "single-quoted")

    def test_dotenv_values_are_parsed_once_and_cached(self):
        self._env_file.write_text("SOME_VAR=first\n")
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(env.read_env_var("SOME_VAR"), "first")
            # Rewriting the file after the first read must not change the
            # already-cached result -- this documents the caching behavior,
            # not just incidentally relies on it.
            self._env_file.write_text("SOME_VAR=second\n")
            self.assertEqual(env.read_env_var("SOME_VAR"), "first")


if __name__ == "__main__":
    unittest.main()
