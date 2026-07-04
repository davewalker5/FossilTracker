"""Locality database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import LOCALITY_FIELDS, connect, _insert_record, _optional_float, _timestamped_payload

def list_localities(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List locality records.

    :param db_path: Optional SQLite database path.
    :return: Locality rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM localities
                ORDER BY country COLLATE NOCASE, region COLLATE NOCASE, locality_name COLLATE NOCASE
                """
            )
        )


def get_locality(locality_id: int | None, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one locality record.

    :param locality_id: Locality primary key.
    :param db_path: Optional SQLite database path.
    :return: Locality row, or None when missing or unset.
    """

    if not locality_id:
        return None
    with connect(db_path) as connection:
        return connection.execute("SELECT * FROM localities WHERE id = ?", (locality_id,)).fetchone()


def create_locality(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a locality record.

    :param values: Locality field values.
    :param db_path: Optional SQLite database path.
    :return: New locality id.
    """

    payload = _timestamped_payload(LOCALITY_FIELDS, values)
    payload["latitude"] = _optional_float(payload.get("latitude"))
    payload["longitude"] = _optional_float(payload.get("longitude"))
    return _insert_record("localities", [*LOCALITY_FIELDS, "created_at", "updated_at"], payload, db_path)


def update_locality(
    locality_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a locality record.

    :param locality_id: Locality primary key.
    :param values: Locality field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(LOCALITY_FIELDS, values)
    payload["latitude"] = _optional_float(payload.get("latitude"))
    payload["longitude"] = _optional_float(payload.get("longitude"))
    assignments = ", ".join([f"{field} = ?" for field in [*LOCALITY_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE localities SET {assignments} WHERE id = ?",
            [payload[field] for field in LOCALITY_FIELDS] + [payload["updated_at"], locality_id],
        )
        connection.commit()


def delete_locality(locality_id: int, db_path: Path | None = None) -> None:
    """Delete one locality record.

    :param locality_id: Locality primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM localities WHERE id = ?", (locality_id,))
        connection.commit()
