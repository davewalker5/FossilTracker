"""Application helper tests."""

from __future__ import annotations

from pathlib import Path

from ui.common import (
    save_uploaded_document,
    save_uploaded_image,
    validate_related_link_url,
)
from ui.provenance import parse_acquisition_date


class UploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getbuffer(self) -> bytes:
        return self._content


def test_save_uploaded_image_uses_configured_image_folder(tmp_path: Path, monkeypatch) -> None:
    image_folder = tmp_path / "images"
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", str(image_folder))

    stored_path = save_uploaded_image(
        UploadedFile("overall view.jpg", b"image-bytes"),
        {"collection_code": "FT-0001"},
    )

    path = Path(stored_path)
    assert path.is_absolute()
    assert path.parent == image_folder
    assert path.name == "FT-0001_overall-view.jpg"
    assert path.read_bytes() == b"image-bytes"


def test_save_uploaded_document_uses_configured_document_folder(tmp_path: Path, monkeypatch) -> None:
    document_folder = tmp_path / "documents"
    monkeypatch.setenv("FOSSIL_TRACKER_DOCUMENTS", str(document_folder))

    stored_path = save_uploaded_document(
        UploadedFile("dealer receipt.pdf", b"document-bytes"),
        {"collection_code": "FT-0001"},
    )

    path = Path(stored_path)
    assert path.is_absolute()
    assert path.parent == document_folder
    assert path.name == "FT-0001_dealer-receipt.pdf"
    assert path.read_bytes() == b"document-bytes"


def test_validate_related_link_url_rejects_empty_and_incomplete_urls() -> None:
    assert validate_related_link_url("") == "URL is required."
    assert (
        validate_related_link_url("fieldnotes.example/page")
        == "Enter a full URL starting with http:// or https://."
    )
    assert (
        validate_related_link_url("https://fieldnotes.example/bad path")
        == "URL cannot contain spaces."
    )
    assert validate_related_link_url("https://fieldnotes.example/page") is None


def test_parse_acquisition_date_accepts_iso_dates_only() -> None:
    assert parse_acquisition_date("2026-07-04").isoformat() == "2026-07-04"
    assert parse_acquisition_date("") is None
    assert parse_acquisition_date("04/07/2026") is None
