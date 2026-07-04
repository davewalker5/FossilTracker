"""Preparation type database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import PREPARATION_TYPE_FIELDS, connect, _insert_record, _timestamped_payload

def list_preparation_types(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List controlled preparation types.

    :param db_path: Optional SQLite database path.
    :return: Preparation type rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM preparation_types
                ORDER BY name COLLATE NOCASE
                """
            )
        )


def create_preparation_type(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a preparation type.

    :param values: Preparation type field values.
    :param db_path: Optional SQLite database path.
    :return: New preparation type id.
    """

    payload = _timestamped_payload(PREPARATION_TYPE_FIELDS, values)
    return _insert_record(
        "preparation_types",
        [*PREPARATION_TYPE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_preparation_type(
    preparation_type_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a preparation type.

    :param preparation_type_id: Preparation type primary key.
    :param values: Preparation type field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(PREPARATION_TYPE_FIELDS, values)
    assignments = ", ".join(
        [f"{field} = ?" for field in [*PREPARATION_TYPE_FIELDS, "updated_at"]]
    )

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE preparation_types SET {assignments} WHERE id = ?",
            [payload[field] for field in PREPARATION_TYPE_FIELDS]
            + [payload["updated_at"], preparation_type_id],
        )
        connection.commit()


def delete_preparation_type(
    preparation_type_id: int, db_path: Path | None = None
) -> None:
    """Delete one preparation type.

    :param preparation_type_id: Preparation type primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM preparation_types WHERE id = ?", (preparation_type_id,))
        connection.commit()

def _find_preparation_type_id(name: str, db_path: Path | None = None) -> int | None:
    """Find the first preparation type id by name.

    :param name: Preparation type name.
    :param db_path: Optional SQLite database path.
    :return: Preparation type id, or None when missing.
    """

    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM preparation_types WHERE name = ? ORDER BY id LIMIT 1",
            (name,),
        ).fetchone()
    return int(row["id"]) if row else None
