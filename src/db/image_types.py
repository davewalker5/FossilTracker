"""Image type reference data operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import IMAGE_TYPE_FIELDS, connect, _insert_record, _timestamped_payload


def list_image_types(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List configured image types."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM image_types
                ORDER BY name COLLATE NOCASE
                """
            )
        )


def create_image_type(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create an image type."""

    payload = _timestamped_payload(IMAGE_TYPE_FIELDS, values)
    return _insert_record(
        "image_types",
        [*IMAGE_TYPE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_image_type(
    image_type_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update an image type."""

    payload = _timestamped_payload(IMAGE_TYPE_FIELDS, values)
    assignments = ", ".join(
        [f"{field} = ?" for field in [*IMAGE_TYPE_FIELDS, "updated_at"]]
    )

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE image_types SET {assignments} WHERE id = ?",
            [payload[field] for field in IMAGE_TYPE_FIELDS]
            + [payload["updated_at"], image_type_id],
        )
        connection.commit()


def delete_image_type(image_type_id: int, db_path: Path | None = None) -> None:
    """Delete one image type."""

    with connect(db_path) as connection:
        connection.execute("DELETE FROM image_types WHERE id = ?", (image_type_id,))
        connection.commit()
