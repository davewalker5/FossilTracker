"""Application helper tests."""

from __future__ import annotations

from pathlib import Path

from fossil_tracker.config import PROJECT_ROOT
from ui.common import (
    delete_managed_image_file,
    save_uploaded_document,
    save_uploaded_image,
    validate_related_link_url,
)
from ui.images import (
    image_date_text,
    image_licence_label,
    image_licence_options,
    option_index,
    option_with_current,
    parse_image_date,
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


def test_delete_managed_image_file_removes_configured_image_file(
    tmp_path: Path, monkeypatch
) -> None:
    image_folder = tmp_path / "images"
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", str(image_folder))
    image_folder.mkdir()
    image_path = image_folder / "FT-0001.jpg"
    image_path.write_bytes(b"image-bytes")

    assert delete_managed_image_file(str(image_path))
    assert not image_path.exists()


def test_delete_managed_image_file_ignores_unmanaged_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", str(tmp_path / "images"))
    unmanaged_path = tmp_path / "other" / "external.jpg"
    unmanaged_path.parent.mkdir()
    unmanaged_path.write_bytes(b"external-image")

    assert not delete_managed_image_file(str(unmanaged_path))
    assert unmanaged_path.read_bytes() == b"external-image"


def test_delete_managed_image_file_handles_project_relative_image(monkeypatch) -> None:
    monkeypatch.delenv("FOSSIL_TRACKER_IMAGES", raising=False)
    image_path = PROJECT_ROOT / "data" / "images" / "delete-test.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"image-bytes")

    try:
        assert delete_managed_image_file("data/images/delete-test.jpg")
        assert not image_path.exists()
    finally:
        image_path.unlink(missing_ok=True)


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


def test_image_date_text_formats_optional_date() -> None:
    assert parse_image_date("2026-07-04").isoformat() == "2026-07-04"
    assert parse_image_date("04/07/2026") is None
    assert image_date_text(parse_image_date("2026-07-04")) == "2026-07-04"
    assert image_date_text(None) == ""


def test_image_licence_options_are_optional() -> None:
    licences = [{"name": "CC BY 4.0"}, {"name": "CC0"}]
    assert image_licence_options(licences) == ["", "CC BY 4.0", "CC0"]
    assert image_licence_label("") == "Not recorded"
    assert image_licence_label("CC0") == "CC0"


def test_option_with_current_preserves_existing_selectbox_values() -> None:
    assert option_with_current(["", "CC0"], "Private") == ["", "CC0", "Private"]
    assert option_with_current(["", "CC0"], "CC0") == ["", "CC0"]
    assert option_index(["", "CC0"], "CC0") == 1
    assert option_index(["", "CC0"], "Missing") == 0
