"""Specimen measurement database operations."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from db.core import (
    SPECIMEN_MEASUREMENT_FIELDS,
    connect,
    _insert_record,
    _optional_int,
    _timestamped_payload,
)


def _rounded_measurement_value(value: Any) -> str:
    """Return a numeric measurement rounded to at most three decimal places."""

    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("measurement value must be numeric") from exc
    if not number.is_finite():
        raise ValueError("measurement value must be finite")

    try:
        rounded = number.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("measurement value is outside the supported range") from exc
    if rounded == 0:
        return "0"
    return format(rounded, "f").rstrip("0").rstrip(".")


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
    payload["value"] = _rounded_measurement_value(payload.get("value"))
    return _insert_record(
        "specimen_measurements",
        [*SPECIMEN_MEASUREMENT_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def update_specimen_measurement(
    measurement_id: int,
    values: dict[str, Any],
    db_path: Path | None = None,
) -> None:
    """Update one specimen measurement record."""

    measurement_type_id = _optional_int(values.get("measurement_type_id"))
    value = _rounded_measurement_value(values.get("value"))
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE specimen_measurements
            SET measurement_type_id = ?, value = ?, updated_at = ?
            WHERE id = ?
            """,
            (measurement_type_id, value, now, measurement_id),
        )
        connection.commit()


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
    measurements: dict[int, str | None],
    db_path: Path | None = None,
    *,
    text_measurement_type_ids: frozenset[int] = frozenset(),
) -> None:
    """Atomically insert, update, or clear measurements for one specimen.

    :param specimen_id: Specimen primary key.
    :param measurements: Values keyed by measurement type id; ``None`` clears a value.
    :param db_path: Optional SQLite database path.
    :param text_measurement_type_ids: Type ids whose values are categorical text.
    :return: None.
    """

    # Use one timestamp for every value saved in this logical operation.
    now = datetime.now(UTC).isoformat(timespec="seconds")
    rows = [
        (
            specimen_id,
            measurement_type_id,
            str(value).strip()
            if measurement_type_id in text_measurement_type_ids
            else _rounded_measurement_value(value),
            now,
            now,
        )
        for measurement_type_id, value in measurements.items()
        if value is not None
    ]
    cleared_type_ids = [
        measurement_type_id
        for measurement_type_id, value in measurements.items()
        if value is None
    ]
    with connect(db_path) as connection:
        # Remove optional values that the user has explicitly cleared.
        connection.executemany(
            """
            DELETE FROM specimen_measurements
            WHERE specimen_id = ? AND measurement_type_id = ?
            """,
            [(specimen_id, measurement_type_id) for measurement_type_id in cleared_type_ids],
        )
        # Upsert the remaining values so repeat saves update the same records.
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
