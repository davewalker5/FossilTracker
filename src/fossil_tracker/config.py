"""Shared paths and constants for Fossil Tracker."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Fossil Tracker"
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "fossil_tracker.sqlite3"
DEFAULT_IMAGE_DIR = DEFAULT_DATA_DIR / "images"
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"


def database_path() -> Path:
    """Return the configured database path."""

    return _configured_path("FOSSIL_TRACKER_DB", DEFAULT_DB_PATH)


def image_dir() -> Path:
    """Return the configured image storage directory."""

    return _configured_path("FOSSIL_TRACKER_IMAGES", DEFAULT_IMAGE_DIR)


def _configured_path(environment_variable: str, default_path: Path) -> Path:
    configured_path = os.environ.get(environment_variable)
    if configured_path:
        return Path(configured_path).expanduser()
    return default_path
