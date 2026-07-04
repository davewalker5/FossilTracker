"""Application helper tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fossil_tracker.app import (
    save_uploaded_document,
    save_uploaded_image,
    validate_related_link_url,
)


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

    def test_save_uploaded_document_uses_configured_document_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            document_folder = Path(temp_dir) / "documents"
            with patch.dict(os.environ, {"FOSSIL_TRACKER_DOCUMENTS": str(document_folder)}):
                stored_path = save_uploaded_document(
                    UploadedFile("dealer receipt.pdf", b"document-bytes"),
                    {"collection_code": "FT-0001"},
                )

            path = Path(stored_path)
            self.assertTrue(path.is_absolute())
            self.assertEqual(path.parent, document_folder)
            self.assertEqual(path.name, "FT-0001_dealer-receipt.pdf")
            self.assertEqual(path.read_bytes(), b"document-bytes")

    def test_validate_related_link_url_rejects_empty_and_incomplete_urls(self) -> None:
        self.assertEqual(validate_related_link_url(""), "URL is required.")
        self.assertEqual(
            validate_related_link_url("fieldnotes.example/page"),
            "Enter a full URL starting with http:// or https://.",
        )
        self.assertEqual(
            validate_related_link_url("https://fieldnotes.example/bad path"),
            "URL cannot contain spaces.",
        )
        self.assertIsNone(validate_related_link_url("https://fieldnotes.example/page"))


if __name__ == "__main__":
    unittest.main()
