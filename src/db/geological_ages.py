"""Geological age database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import GEOLOGICAL_AGE_FIELDS, connect, _insert_record, _optional_float, _timestamped_payload

def list_geological_ages(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List geological age records.

    :param db_path: Optional SQLite database path.
    :return: Geological age rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM geological_ages
                ORDER BY max_ma DESC, min_ma DESC, period COLLATE NOCASE
                """
            )
        )


def get_geological_age(
    geological_age_id: int | None, db_path: Path | None = None
) -> sqlite3.Row | None:
    """Fetch one geological age record.

    :param geological_age_id: Geological age primary key.
    :param db_path: Optional SQLite database path.
    :return: Geological age row, or None when missing or unset.
    """

    if not geological_age_id:
        return None
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM geological_ages WHERE id = ?", (geological_age_id,)
        ).fetchone()


def create_geological_age(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a geological age record.

    :param values: Geological age field values.
    :param db_path: Optional SQLite database path.
    :return: New geological age id.
    """

    payload = _timestamped_payload(GEOLOGICAL_AGE_FIELDS, values)
    payload["min_ma"] = _optional_float(payload.get("min_ma"))
    payload["max_ma"] = _optional_float(payload.get("max_ma"))
    return _insert_record(
        "geological_ages",
        [*GEOLOGICAL_AGE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_geological_age(
    geological_age_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a geological age record.

    :param geological_age_id: Geological age primary key.
    :param values: Geological age field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(GEOLOGICAL_AGE_FIELDS, values)
    payload["min_ma"] = _optional_float(payload.get("min_ma"))
    payload["max_ma"] = _optional_float(payload.get("max_ma"))
    assignments = ", ".join([f"{field} = ?" for field in [*GEOLOGICAL_AGE_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE geological_ages SET {assignments} WHERE id = ?",
            [payload[field] for field in GEOLOGICAL_AGE_FIELDS]
            + [payload["updated_at"], geological_age_id],
        )
        connection.commit()


def delete_geological_age(
    geological_age_id: int, db_path: Path | None = None
) -> None:
    """Delete one geological age record.

    :param geological_age_id: Geological age primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM geological_ages WHERE id = ?", (geological_age_id,))
        connection.commit()

def _find_geological_age_id(period: str, db_path: Path | None = None) -> int | None:
    """Find the first geological age id for a period.

    :param period: Geological period name.
    :param db_path: Optional SQLite database path.
    :return: Geological age id, or None when missing.
    """

    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM geological_ages WHERE period = ? ORDER BY id LIMIT 1",
            (period,),
        ).fetchone()
    return int(row["id"]) if row else None
