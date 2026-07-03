"""Configuration tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fossil_tracker.config import DEFAULT_DB_PATH, database_path


class ConfigTests(unittest.TestCase):
    def test_database_path_defaults_to_project_data_path(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(database_path(), DEFAULT_DB_PATH)

    def test_database_path_uses_environment_variable_when_set(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_DB": "/tmp/fossils.sqlite3"}):
            self.assertEqual(str(database_path()), "/tmp/fossils.sqlite3")

    def test_database_path_expands_user_home(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_DB": "~/fossils.sqlite3"}):
            self.assertFalse(str(database_path()).startswith("~"))

    def test_database_path_uses_default_when_environment_variable_is_blank(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_DB": ""}):
            self.assertEqual(database_path(), DEFAULT_DB_PATH)


if __name__ == "__main__":
    unittest.main()
