"""Specimen image database operations."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.core import IMAGE_FIELDS, connect, _optional_int

def list_specimen_images(
    specimen_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List images for one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    :return: Image rows linked to the specimen.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT
                    specimen_images.*,
                    image_types.name AS image_type
                FROM specimen_images
                LEFT JOIN image_types
                    ON image_types.id = specimen_images.image_type_id
                WHERE specimen_id = ?
                ORDER BY date_taken DESC, created_at DESC, id DESC
                """,
                (specimen_id,),
            )
        )


def create_specimen_image(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create an image record.

    :param values: Image field values.
    :param db_path: Optional SQLite database path.
    :return: New image id.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in IMAGE_FIELDS}
    payload["image_type_id"] = _optional_int(payload.get("image_type_id"))
    payload["created_at"] = now
    payload["updated_at"] = now
    fields = [*IMAGE_FIELDS, "created_at", "updated_at"]

    with connect(db_path) as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO specimen_images ({', '.join(fields)})
            VALUES ({', '.join(['?'] * len(fields))})
            """,
            [payload[field] for field in fields],
        )
        connection.commit()
        return int(cursor.lastrowid)


def update_specimen_image(
    image_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update an image record.

    :param image_id: Image primary key.
    :param values: Image field values.
    :param db_path: Optional SQLite database path.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in IMAGE_FIELDS}
    payload["image_type_id"] = _optional_int(payload.get("image_type_id"))
    assignments = ", ".join([f"{field} = ?" for field in [*IMAGE_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE specimen_images SET {assignments} WHERE id = ?",
            [payload[field] for field in IMAGE_FIELDS] + [now, image_id],
        )
        connection.commit()


def delete_specimen_image(image_id: int, db_path: Path | None = None) -> None:
    """Delete one image record.

    :param image_id: Image primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimen_images WHERE id = ?", (image_id,))
        connection.commit()
