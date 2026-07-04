"""Configuration tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fossil_tracker.config import (
    DEFAULT_DB_PATH,
    DEFAULT_DOCUMENT_DIR,
    DEFAULT_IMAGE_DIR,
    database_path,
    document_dir,
    image_dir,
)


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

    def test_image_dir_defaults_to_project_image_path(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(image_dir(), DEFAULT_IMAGE_DIR)

    def test_image_dir_uses_environment_variable_when_set(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_IMAGES": "/tmp/fossil-images"}):
            self.assertEqual(str(image_dir()), "/tmp/fossil-images")

    def test_image_dir_expands_user_home(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_IMAGES": "~/fossil-images"}):
            self.assertFalse(str(image_dir()).startswith("~"))

    def test_image_dir_uses_default_when_environment_variable_is_blank(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_IMAGES": ""}):
            self.assertEqual(image_dir(), DEFAULT_IMAGE_DIR)

    def test_document_dir_defaults_to_project_document_path(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(document_dir(), DEFAULT_DOCUMENT_DIR)

    def test_document_dir_uses_environment_variable_when_set(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_DOCUMENTS": "/tmp/fossil-documents"}):
            self.assertEqual(str(document_dir()), "/tmp/fossil-documents")

    def test_document_dir_expands_user_home(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_DOCUMENTS": "~/fossil-documents"}):
            self.assertFalse(str(document_dir()).startswith("~"))

    def test_document_dir_uses_default_when_environment_variable_is_blank(self) -> None:
        with patch.dict(os.environ, {"FOSSIL_TRACKER_DOCUMENTS": ""}):
            self.assertEqual(document_dir(), DEFAULT_DOCUMENT_DIR)


if __name__ == "__main__":
    unittest.main()
