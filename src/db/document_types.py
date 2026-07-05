"""Document type reference data operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import DOCUMENT_TYPE_FIELDS, connect, _insert_record, _timestamped_payload


def list_document_types(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List configured document types."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM document_types
                ORDER BY name COLLATE NOCASE
                """
            )
        )


def create_document_type(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a document type."""

    payload = _timestamped_payload(DOCUMENT_TYPE_FIELDS, values)
    return _insert_record(
        "document_types",
        [*DOCUMENT_TYPE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_document_type(
    document_type_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update a document type."""

    payload = _timestamped_payload(DOCUMENT_TYPE_FIELDS, values)
    assignments = ", ".join(
        [f"{field} = ?" for field in [*DOCUMENT_TYPE_FIELDS, "updated_at"]]
    )

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE document_types SET {assignments} WHERE id = ?",
            [payload[field] for field in DOCUMENT_TYPE_FIELDS]
            + [payload["updated_at"], document_type_id],
        )
        connection.commit()


def delete_document_type(document_type_id: int, db_path: Path | None = None) -> None:
    """Delete one document type."""

    with connect(db_path) as connection:
        connection.execute("DELETE FROM document_types WHERE id = ?", (document_type_id,))
        connection.commit()
