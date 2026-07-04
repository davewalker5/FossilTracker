"""Acquisition and document database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from db.core import (
    ACQUISITION_DOCUMENT_FIELDS,
    ACQUISITION_FIELDS,
    connect,
    _insert_record,
    _optional_int,
    _timestamped_payload,
)

def list_acquisitions(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List acquisition/provenance records.

    :param db_path: Optional SQLite database path.
    :return: Acquisition rows ordered for display.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM acquisitions
                ORDER BY acquisition_date DESC, source_name COLLATE NOCASE, id DESC
                """
            )
        )


def get_acquisition(
    acquisition_id: int | None, db_path: Path | None = None
) -> sqlite3.Row | None:
    """Fetch one acquisition record.

    :param acquisition_id: Acquisition primary key.
    :param db_path: Optional SQLite database path.
    :return: Acquisition row, or None when missing or unset.
    """

    if not acquisition_id:
        return None
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM acquisitions WHERE id = ?", (acquisition_id,)
        ).fetchone()


def create_acquisition(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create an acquisition record.

    :param values: Acquisition field values.
    :param db_path: Optional SQLite database path.
    :return: New acquisition id.
    """

    payload = _timestamped_payload(ACQUISITION_FIELDS, values)
    payload["ethical_confidence"] = payload.get("ethical_confidence") or "Unknown"
    return _insert_record(
        "acquisitions",
        [*ACQUISITION_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_acquisition(
    acquisition_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update an acquisition record.

    :param acquisition_id: Acquisition primary key.
    :param values: Acquisition field values.
    :param db_path: Optional SQLite database path.
    """

    payload = _timestamped_payload(ACQUISITION_FIELDS, values)
    payload["ethical_confidence"] = payload.get("ethical_confidence") or "Unknown"
    assignments = ", ".join([f"{field} = ?" for field in [*ACQUISITION_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE acquisitions SET {assignments} WHERE id = ?",
            [payload[field] for field in ACQUISITION_FIELDS] + [payload["updated_at"], acquisition_id],
        )
        connection.commit()


def list_acquisition_documents(
    acquisition_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List documents linked to one acquisition.

    :param acquisition_id: Acquisition primary key.
    :param db_path: Optional SQLite database path.
    :return: Linked acquisition document rows.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM acquisition_documents
                WHERE acquisition_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (acquisition_id,),
            )
        )


def has_acquisition_documents(
    acquisition_id: int | None, db_path: Path | None = None
) -> bool:
    """Return whether an acquisition has linked documents.

    :param acquisition_id: Acquisition primary key.
    :param db_path: Optional SQLite database path.
    :return: True when at least one document is linked.
    """

    if not acquisition_id:
        return False
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM acquisition_documents
            WHERE acquisition_id = ?
            LIMIT 1
            """,
            (acquisition_id,),
        ).fetchone()
    return row is not None


def create_acquisition_document(
    values: dict[str, Any], db_path: Path | None = None
) -> int:
    """Create an acquisition document record.

    :param values: Acquisition document field values.
    :param db_path: Optional SQLite database path.
    :return: New acquisition document id.
    """

    payload = _timestamped_payload(ACQUISITION_DOCUMENT_FIELDS, values)
    payload["acquisition_id"] = _optional_int(payload.get("acquisition_id"))
    return _insert_record(
        "acquisition_documents",
        [*ACQUISITION_DOCUMENT_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def delete_acquisition_document(
    document_id: int, db_path: Path | None = None
) -> None:
    """Delete one acquisition document record.

    :param document_id: Acquisition document primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM acquisition_documents WHERE id = ?", (document_id,))
        connection.commit()
