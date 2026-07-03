"""Shared paths and constants for Fossil Tracker."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Fossil Tracker"
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "fossil_tracker.sqlite3"
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"


def database_path() -> Path:
    """Return the configured database path."""

    return Path(os.environ.get("FOSSIL_TRACKER_DB", DEFAULT_DB_PATH)).expanduser()
