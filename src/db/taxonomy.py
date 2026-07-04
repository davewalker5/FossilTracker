"""Taxonomy database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import TAXONOMY_FIELDS, connect, _insert_record, _timestamped_payload

def list_taxonomy(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List taxonomy records.

    :param db_path: Optional SQLite database path.
    :return: Taxonomy rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM taxonomy
                ORDER BY genus COLLATE NOCASE, species COLLATE NOCASE, identification_notes COLLATE NOCASE
                """
            )
        )


def get_taxonomy(taxon_id: int | None, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one taxonomy record.

    :param taxon_id: Taxonomy primary key.
    :param db_path: Optional SQLite database path.
    :return: Taxonomy row, or None when missing or unset.
    """

    if not taxon_id:
        return None
    with connect(db_path) as connection:
        return connection.execute("SELECT * FROM taxonomy WHERE id = ?", (taxon_id,)).fetchone()


def create_taxonomy(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a taxonomy record.

    :param values: Taxonomy field values.
    :param db_path: Optional SQLite database path.
    :return: New taxonomy id.
    """

    payload = _timestamped_payload(TAXONOMY_FIELDS, values)
    payload["identification_confidence"] = payload.get("identification_confidence") or "Unknown"
    return _insert_record("taxonomy", [*TAXONOMY_FIELDS, "created_at", "updated_at"], payload, db_path)


def update_taxonomy(
    taxon_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a taxonomy record.

    :param taxon_id: Taxonomy primary key.
    :param values: Taxonomy field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(TAXONOMY_FIELDS, values)
    payload["identification_confidence"] = payload.get("identification_confidence") or "Unknown"
    assignments = ", ".join([f"{field} = ?" for field in [*TAXONOMY_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE taxonomy SET {assignments} WHERE id = ?",
            [payload[field] for field in TAXONOMY_FIELDS] + [payload["updated_at"], taxon_id],
        )
        connection.commit()


def delete_taxonomy(taxon_id: int, db_path: Path | None = None) -> None:
    """Delete one taxonomy record.

    :param taxon_id: Taxonomy primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM taxonomy WHERE id = ?", (taxon_id,))
        connection.commit()
