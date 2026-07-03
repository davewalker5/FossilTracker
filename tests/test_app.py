"""Application helper tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fossil_tracker.app import save_uploaded_image


class UploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getbuffer(self) -> bytes:
        return self._content


class AppHelperTests(unittest.TestCase):
    def test_save_uploaded_image_uses_configured_image_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_folder = Path(temp_dir) / "images"
            with patch.dict(os.environ, {"FOSSIL_TRACKER_IMAGES": str(image_folder)}):
                stored_path = save_uploaded_image(
                    UploadedFile("overall view.jpg", b"image-bytes"),
                    {"collection_code": "FT-0001"},
                )

            path = Path(stored_path)
            self.assertTrue(path.is_absolute())
            self.assertEqual(path.parent, image_folder)
            self.assertEqual(path.name, "FT-0001_overall-view.jpg")
            self.assertEqual(path.read_bytes(), b"image-bytes")


if __name__ == "__main__":
    unittest.main()
