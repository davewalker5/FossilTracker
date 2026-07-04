"""Measurement type database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import MEASUREMENT_TYPE_FIELDS, connect, _insert_record, _timestamped_payload

def list_measurement_types(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List configured measurement types.

    :param db_path: Optional SQLite database path.
    :return: Measurement type rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM measurement_types
                ORDER BY name COLLATE NOCASE
                """
            )
        )


def get_measurement_type(
    measurement_type_id: int | None, db_path: Path | None = None
) -> sqlite3.Row | None:
    """Fetch one measurement type.

    :param measurement_type_id: Measurement type primary key.
    :param db_path: Optional SQLite database path.
    :return: Measurement type row, or None when missing or unset.
    """

    if not measurement_type_id:
        return None
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM measurement_types WHERE id = ?", (measurement_type_id,)
        ).fetchone()


def create_measurement_type(
    values: dict[str, Any], db_path: Path | None = None
) -> int:
    """Create a measurement type.

    :param values: Measurement type field values.
    :param db_path: Optional SQLite database path.
    :return: New measurement type id.
    """

    payload = _timestamped_payload(MEASUREMENT_TYPE_FIELDS, values)
    return _insert_record(
        "measurement_types",
        [*MEASUREMENT_TYPE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_measurement_type(
    measurement_type_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a measurement type.

    :param measurement_type_id: Measurement type primary key.
    :param values: Measurement type field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(MEASUREMENT_TYPE_FIELDS, values)
    assignments = ", ".join(
        [f"{field} = ?" for field in [*MEASUREMENT_TYPE_FIELDS, "updated_at"]]
    )

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE measurement_types SET {assignments} WHERE id = ?",
            [payload[field] for field in MEASUREMENT_TYPE_FIELDS]
            + [payload["updated_at"], measurement_type_id],
        )
        connection.commit()


def delete_measurement_type(
    measurement_type_id: int, db_path: Path | None = None
) -> None:
    """Delete one measurement type.

    :param measurement_type_id: Measurement type primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM measurement_types WHERE id = ?", (measurement_type_id,))
        connection.commit()
