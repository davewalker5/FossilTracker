"""Specimen measurement database operations."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.core import (
    SPECIMEN_MEASUREMENT_FIELDS,
    connect,
    _insert_record,
    _optional_int,
    _timestamped_payload,
)

def list_specimen_measurements(
    specimen_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List measurements recorded for one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    :return: Measurement rows linked to the specimen.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT
                    specimen_measurements.*,
                    measurement_types.name AS measurement_name,
                    measurement_types.unit AS measurement_unit
                FROM specimen_measurements
                JOIN measurement_types
                    ON measurement_types.id = specimen_measurements.measurement_type_id
                WHERE specimen_measurements.specimen_id = ?
                ORDER BY measurement_types.name COLLATE NOCASE
                """,
                (specimen_id,),
            )
        )


def create_specimen_measurement(
    values: dict[str, Any], db_path: Path | None = None
) -> int:
    """Create a specimen measurement record.

    :param values: Specimen measurement field values.
    :param db_path: Optional SQLite database path.
    :return: New specimen measurement id.
    """

    payload = _timestamped_payload(SPECIMEN_MEASUREMENT_FIELDS, values)
    payload["specimen_id"] = _optional_int(payload.get("specimen_id"))
    payload["measurement_type_id"] = _optional_int(payload.get("measurement_type_id"))
    return _insert_record(
        "specimen_measurements",
        [*SPECIMEN_MEASUREMENT_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def delete_specimen_measurement(
    measurement_id: int, db_path: Path | None = None
) -> None:
    """Delete one specimen measurement record.

    :param measurement_id: Specimen measurement primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimen_measurements WHERE id = ?", (measurement_id,))
        connection.commit()


def save_specimen_measurements(
    specimen_id: int,
    measurements: dict[int, str],
    db_path: Path | None = None,
) -> None:
    """Atomically insert or update several measurements for one specimen."""

    now = datetime.now(UTC).isoformat(timespec="seconds")
    rows = [
        (specimen_id, measurement_type_id, value, now, now)
        for measurement_type_id, value in measurements.items()
    ]
    with connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO specimen_measurements
                (specimen_id, measurement_type_id, value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(specimen_id, measurement_type_id) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            rows,
        )
        connection.commit()
