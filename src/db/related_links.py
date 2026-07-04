"""Related link database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import RELATED_LINK_FIELDS, connect, _insert_record, _optional_int, _timestamped_payload

def list_related_links(
    specimen_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List Field Notes links for one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    :return: Related link rows linked to the specimen.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM specimen_related_links
                WHERE specimen_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (specimen_id,),
            )
        )


def create_related_link(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a Field Notes link record.

    :param values: Related link field values.
    :param db_path: Optional SQLite database path.
    :return: New related link id.
    """

    payload = _timestamped_payload(RELATED_LINK_FIELDS, values)
    payload["specimen_id"] = _optional_int(payload.get("specimen_id"))
    return _insert_record(
        "specimen_related_links",
        [*RELATED_LINK_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def delete_related_link(link_id: int, db_path: Path | None = None) -> None:
    """Delete one Field Notes link record.

    :param link_id: Related link primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimen_related_links WHERE id = ?", (link_id,))
        connection.commit()
