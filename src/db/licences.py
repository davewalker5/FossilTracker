"""Licence reference data operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import LICENCE_FIELDS, connect, _insert_record, _timestamped_payload


def list_licences(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List configured licences.

    :param db_path: Optional SQLite database path.
    :return: Licence rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM licences
                ORDER BY name COLLATE NOCASE
                """
            )
        )


def get_licence(licence_id: int | None, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one licence.

    :param licence_id: Licence primary key.
    :param db_path: Optional SQLite database path.
    :return: Licence row, or None when missing or unset.
    """

    if not licence_id:
        return None
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM licences WHERE id = ?", (licence_id,)
        ).fetchone()


def create_licence(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a licence.

    :param values: Licence field values.
    :param db_path: Optional SQLite database path.
    :return: New licence id.
    """

    payload = _timestamped_payload(LICENCE_FIELDS, values)
    return _insert_record(
        "licences",
        [*LICENCE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_licence(
    licence_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a licence.

    :param licence_id: Licence primary key.
    :param values: Licence field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(LICENCE_FIELDS, values)
    assignments = ", ".join([f"{field} = ?" for field in [*LICENCE_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE licences SET {assignments} WHERE id = ?",
            [payload[field] for field in LICENCE_FIELDS] + [payload["updated_at"], licence_id],
        )
        connection.commit()


def delete_licence(licence_id: int, db_path: Path | None = None) -> None:
    """Delete one licence.

    :param licence_id: Licence primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM licences WHERE id = ?", (licence_id,))
        connection.commit()
