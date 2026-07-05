"""Shared database connection, migration, and coercion helpers."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fossil_tracker.config import MIGRATIONS_PATH, database_path

SPECIMEN_FIELDS = [
    "collection_code",
    "title",
    "common_name",
    "taxon_id",
    "geological_age_id",
    "locality_id",
    "acquisition_id",
    "public_visible",
    "description",
    "preparation_type_id",
    "storage_location",
]

IMAGE_FIELDS = [
    "specimen_id",
    "image_path",
    "image_type_id",
    "caption",
    "photographer",
    "licence",
    "date_taken",
    "notes",
]

OBSERVATION_FIELDS = [
    "specimen_id",
    "observation_date",
    "observation_type",
    "notes",
    "public_visible",
]

TAXONOMY_FIELDS = [
    "kingdom",
    "phylum",
    "class_name",
    "subclass",
    "order_name",
    "family",
    "genus",
    "species",
    "identification_confidence",
    "identification_notes",
]

LOCALITY_FIELDS = [
    "locality_name",
    "formation",
    "member",
    "region",
    "country",
    "latitude",
    "longitude",
    "locality_precision",
    "locality_notes",
]

GEOLOGICAL_AGE_FIELDS = [
    "era",
    "period",
    "epoch",
    "stage",
    "min_ma",
    "max_ma",
]

PREPARATION_TYPE_FIELDS = [
    "name",
    "description",
]

LICENCE_FIELDS = [
    "name",
    "notes",
    "url",
]

MEASUREMENT_TYPE_FIELDS = [
    "name",
    "unit",
    "description",
]

IMAGE_TYPE_FIELDS = [
    "name",
    "description",
]

DOCUMENT_TYPE_FIELDS = [
    "name",
    "description",
]

ACQUISITION_FIELDS = [
    "acquisition_date",
    "source_name",
    "source_type",
    "seller_url",
    "purchase_price",
    "currency",
    "provenance_summary",
    "legality_notes",
    "ethical_confidence",
    "notes",
]

ACQUISITION_DOCUMENT_FIELDS = [
    "acquisition_id",
    "document_path",
    "document_type_id",
    "title",
    "notes",
]

RELATED_LINK_FIELDS = [
    "specimen_id",
    "url",
    "title",
    "description",
]

SPECIMEN_MEASUREMENT_FIELDS = [
    "specimen_id",
    "measurement_type_id",
    "value",
]



def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row dictionaries and foreign keys enabled.

    :param db_path: Optional SQLite database path.
    :return: Configured SQLite connection.
    """

    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_migrations(db_path: Path | None = None) -> None:
    """Apply outstanding yoyo migrations to the configured database.

    :param db_path: Optional SQLite database path.
    """

    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from yoyo import get_backend, read_migrations
    except ImportError as exc:
        raise RuntimeError(
            "yoyo-migrations is required to initialise the database. "
            "Install the project dependencies with `pip install -e .`."
        ) from exc

    backend = get_backend(f"sqlite:///{path}")
    migrations = read_migrations(str(MIGRATIONS_PATH))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))

def _timestamped_payload(fields: list[str], values: dict[str, Any]) -> dict[str, Any]:
    """Build an insert payload with created and updated timestamps.

    :param fields: Field names to copy from values.
    :param values: Input values.
    :return: Payload dictionary including timestamps.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in fields}
    payload["created_at"] = now
    payload["updated_at"] = now
    return payload


def _insert_record(
    table: str,
    fields: list[str],
    payload: dict[str, Any],
    db_path: Path | None = None,
) -> int:
    """Insert one row into a table.

    :param table: Target table name.
    :param fields: Ordered field names to insert.
    :param payload: Values keyed by field name.
    :param db_path: Optional SQLite database path.
    :return: New record id.
    """

    placeholders = ", ".join(["?"] * len(fields))
    with connect(db_path) as connection:
        cursor = connection.execute(
            f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})",
            [payload[field] for field in fields],
        )
        record_id = int(cursor.lastrowid)
        connection.commit()
    return record_id

def _optional_int(value: Any) -> int | None:
    """Convert an optional value to an integer.

    :param value: Raw value.
    :return: Integer value, or None when blank.
    """

    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    """Convert an optional value to a float.

    :param value: Raw value.
    :return: Float value, or None when blank.
    """

    if value is None or value == "":
        return None
    return float(value)
