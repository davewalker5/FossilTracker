"""Configuration tests."""

from __future__ import annotations

from fossil_tracker.config import (
    DEFAULT_DB_PATH,
    DEFAULT_DOCUMENT_DIR,
    DEFAULT_EXPORT_DIR,
    DEFAULT_IMAGE_DIR,
    database_path,
    document_dir,
    export_dir,
    image_dir,
)


def test_database_path_defaults_to_project_data_path(monkeypatch) -> None:
    monkeypatch.delenv("FOSSIL_TRACKER_DB", raising=False)

    assert database_path() == DEFAULT_DB_PATH


def test_database_path_uses_environment_variable_when_set(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_DB", "/tmp/fossils.sqlite3")

    assert str(database_path()) == "/tmp/fossils.sqlite3"


def test_database_path_expands_user_home(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_DB", "~/fossils.sqlite3")

    assert not str(database_path()).startswith("~")


def test_database_path_uses_default_when_environment_variable_is_blank(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_DB", "")

    assert database_path() == DEFAULT_DB_PATH


def test_image_dir_defaults_to_project_image_path(monkeypatch) -> None:
    monkeypatch.delenv("FOSSIL_TRACKER_IMAGES", raising=False)

    assert image_dir() == DEFAULT_IMAGE_DIR


def test_image_dir_uses_environment_variable_when_set(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", "/tmp/fossil-images")

    assert str(image_dir()) == "/tmp/fossil-images"


def test_image_dir_expands_user_home(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", "~/fossil-images")

    assert not str(image_dir()).startswith("~")


def test_image_dir_uses_default_when_environment_variable_is_blank(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", "")

    assert image_dir() == DEFAULT_IMAGE_DIR


def test_document_dir_defaults_to_project_document_path(monkeypatch) -> None:
    monkeypatch.delenv("FOSSIL_TRACKER_DOCUMENTS", raising=False)

    assert document_dir() == DEFAULT_DOCUMENT_DIR


def test_document_dir_uses_environment_variable_when_set(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_DOCUMENTS", "/tmp/fossil-documents")

    assert str(document_dir()) == "/tmp/fossil-documents"


def test_document_dir_expands_user_home(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_DOCUMENTS", "~/fossil-documents")

    assert not str(document_dir()).startswith("~")


def test_document_dir_uses_default_when_environment_variable_is_blank(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_DOCUMENTS", "")

    assert document_dir() == DEFAULT_DOCUMENT_DIR


def test_export_dir_defaults_to_project_export_path(monkeypatch) -> None:
    monkeypatch.delenv("FOSSIL_TRACKER_EXPORT", raising=False)

    assert export_dir() == DEFAULT_EXPORT_DIR


def test_export_dir_uses_environment_variable_when_set(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_EXPORT", "/tmp/fossil-exports")

    assert str(export_dir()) == "/tmp/fossil-exports"


def test_export_dir_expands_user_home(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_EXPORT", "~/fossil-exports")

    assert not str(export_dir()).startswith("~")


def test_export_dir_uses_default_when_environment_variable_is_blank(monkeypatch) -> None:
    monkeypatch.setenv("FOSSIL_TRACKER_EXPORT", "")

    assert export_dir() == DEFAULT_EXPORT_DIR
