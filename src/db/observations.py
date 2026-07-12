"""Observation note database operations."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.core import OBSERVATION_FIELDS, connect

def list_observations(
    specimen_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List observations for one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    :return: Observation rows linked to the specimen.
    """

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM observations
                WHERE specimen_id = ?
                ORDER BY observation_date DESC, created_at DESC, id DESC
                """,
                (specimen_id,),
            )
        )


def create_observation(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create an observation record.

    :param values: Observation field values.
    :param db_path: Optional SQLite database path.
    :return: New observation id.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in OBSERVATION_FIELDS}
    payload["created_at"] = now
    payload["updated_at"] = now
    fields = [*OBSERVATION_FIELDS, "created_at", "updated_at"]

    with connect(db_path) as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO observations ({', '.join(fields)})
            VALUES ({', '.join(['?'] * len(fields))})
            """,
            [payload[field] for field in fields],
        )
        connection.commit()
        return int(cursor.lastrowid)


def update_observation(
    observation_id: int, values: dict[str, Any], db_path: Path | None = None
) -> None:
    """Update an observation record.

    :param observation_id: Observation primary key.
    :param values: Observation field values.
    :param db_path: Optional SQLite database path.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in OBSERVATION_FIELDS}
    assignments = ", ".join(
        [f"{field} = ?" for field in [*OBSERVATION_FIELDS, "updated_at"]]
    )

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE observations SET {assignments} WHERE id = ?",
            [payload[field] for field in OBSERVATION_FIELDS] + [now, observation_id],
        )
        connection.commit()


def delete_observation(observation_id: int, db_path: Path | None = None) -> None:
    """Delete one observation record.

    :param observation_id: Observation primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM observations WHERE id = ?", (observation_id,))
        connection.commit()
