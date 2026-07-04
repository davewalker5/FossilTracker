"""Specimen database operations."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.acquisitions import create_acquisition
from db.core import SPECIMEN_FIELDS, connect, _optional_int
from db.geological_ages import _find_geological_age_id
from db.localities import create_locality
from db.preparation_types import _find_preparation_type_id
from db.taxonomy import create_taxonomy

def specimen_count(db_path: Path | None = None) -> int:
    """Return the number of registered specimens.

    :param db_path: Optional SQLite database path.
    :return: Count of specimen records.
    """

    with connect(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM specimens").fetchone()
    return int(row["count"])


def list_specimens(
    db_path: Path | None = None,
    search: str = "",
    confidence: str = "All",
    documented_only: bool = False,
) -> list[sqlite3.Row]:
    """List specimens with simple filters for the Streamlit register view.

    :param db_path: Optional SQLite database path.
    :param search: Free-text search term.
    :param confidence: Ethical confidence filter, or "All".
    :param documented_only: When true, only include specimens with acquisition documents.
    :return: Matching specimen rows.
    """

    clauses: list[str] = []
    params: list[Any] = []

    if search.strip():
        clauses.append(
            """(
                collection_code LIKE ?
                OR title LIKE ?
                OR common_name LIKE ?
                OR taxonomy.genus LIKE ?
                OR taxonomy.species LIKE ?
                OR taxonomy.identification_notes LIKE ?
                OR localities.locality_name LIKE ?
                OR localities.formation LIKE ?
                OR localities.region LIKE ?
                OR localities.country LIKE ?
                OR geological_ages.period LIKE ?
                OR geological_ages.epoch LIKE ?
                OR geological_ages.stage LIKE ?
                OR acquisitions.source_name LIKE ?
                OR acquisitions.provenance_summary LIKE ?
            )"""
        )
        term = f"%{search.strip()}%"
        params.extend([term] * 15)

    if confidence != "All":
        clauses.append("acquisitions.ethical_confidence = ?")
        params.append(confidence)

    if documented_only:
        # Documentation is inferred from linked document rows rather than a denormalized flag.
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM acquisition_documents
                WHERE acquisition_documents.acquisition_id = specimens.acquisition_id
            )
            """
        )

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT specimens.*
        FROM specimens
        LEFT JOIN taxonomy ON taxonomy.id = specimens.taxon_id
        LEFT JOIN localities ON localities.id = specimens.locality_id
        LEFT JOIN geological_ages ON geological_ages.id = specimens.geological_age_id
        LEFT JOIN acquisitions ON acquisitions.id = specimens.acquisition_id
        {where}
        ORDER BY collection_code COLLATE NOCASE, created_at DESC
    """

    with connect(db_path) as connection:
        return list(connection.execute(sql, params))


def get_specimen(specimen_id: int, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one specimen by id.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    :return: Specimen row, or None when missing.
    """

    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM specimens WHERE id = ?", (specimen_id,)
        ).fetchone()


def next_collection_code(db_path: Path | None = None, prefix: str = "FT") -> str:
    """Return the next collection code for the configured prefix.

    :param db_path: Optional SQLite database path.
    :param prefix: Collection code prefix.
    :return: Next collection code in prefix-NNNN format.
    """

    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    highest = 0
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT collection_code FROM specimens WHERE collection_code LIKE ?",
            (f"{prefix}-%",),
        )

        for row in rows:
            match = pattern.match(row["collection_code"] or "")
            if match:
                highest = max(highest, int(match.group(1)))

    return f"{prefix}-{highest + 1:04d}"


def create_specimen(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a specimen.

    :param values: Editable specimen field values.
    :param db_path: Optional SQLite database path.
    :return: New specimen id.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in SPECIMEN_FIELDS}
    _coerce_specimen_foreign_keys(payload)
    payload["created_at"] = now
    payload["updated_at"] = now

    fields = [*SPECIMEN_FIELDS, "created_at", "updated_at"]
    placeholders = ", ".join(["?"] * len(fields))
    sql = f"INSERT INTO specimens ({', '.join(fields)}) VALUES ({placeholders})"

    with connect(db_path) as connection:
        cursor = connection.execute(sql, [payload[field] for field in fields])
        connection.commit()
        return int(cursor.lastrowid)


def update_specimen(specimen_id: int, values: dict[str, Any], db_path: Path | None = None) -> None:
    """Update the editable fields for a specimen.

    :param specimen_id: Specimen primary key.
    :param values: Editable specimen field values.
    :param db_path: Optional SQLite database path.
    """

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in SPECIMEN_FIELDS}
    _coerce_specimen_foreign_keys(payload)
    payload["updated_at"] = now
    assignments = ", ".join([f"{field} = ?" for field in [*SPECIMEN_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE specimens SET {assignments} WHERE id = ?",
            [payload[field] for field in SPECIMEN_FIELDS] + [now, specimen_id],
        )
        connection.commit()


def delete_specimen(specimen_id: int, db_path: Path | None = None) -> None:
    """Delete one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimens WHERE id = ?", (specimen_id,))
        connection.commit()


def seed_specimens(db_path: Path | None = None) -> int:
    """Create the suggested starter record when the register is empty.

    :param db_path: Optional SQLite database path.
    :return: Number of starter specimens created.
    """

    if specimen_count(db_path) > 0:
        return 0

    ammonite_taxon_id = create_taxonomy(
        {
            "kingdom": "Animalia",
            "phylum": "Mollusca",
            "class_name": "Cephalopoda",
            "identification_confidence": "Unknown",
            "identification_notes": "Ammonoidea, identification pending",
        },
        db_path,
    )
    madagascar_locality_id = create_locality(
        {
            "locality_name": "Exact locality unknown",
            "country": "Madagascar",
            "locality_precision": "Country only",
            "locality_notes": "Unknown",
        },
        db_path,
    )
    jurassic_age_id = _find_geological_age_id("Jurassic", db_path)
    split_polished_id = _find_preparation_type_id("Split and polished", db_path)
    ammonite_acquisition_id = create_acquisition(
        {
            "source_name": "",
            "provenance_summary": "",
            "legality_notes": "",
            "ethical_confidence": "Unknown",
        },
        db_path,
    )

    create_specimen(
        {
            "collection_code": "FT-0001",
            "title": "Split and polished Madagascan ammonite",
            "common_name": "Ammonite",
            "taxon_id": ammonite_taxon_id,
            "geological_age_id": jurassic_age_id,
            "locality_id": madagascar_locality_id,
            "acquisition_id": ammonite_acquisition_id,
            "description": "Polished cross-section showing chamber structure.",
            "preparation_type_id": split_polished_id,
            "public_visible": True,
        },
        db_path=db_path,
    )
    return 1

def _coerce_specimen_foreign_keys(payload: dict[str, Any]) -> None:
    """Normalize specimen foreign-key and boolean values in place.

    :param payload: Specimen insert/update payload.
    """

    for field in ["taxon_id", "geological_age_id", "locality_id", "preparation_type_id", "acquisition_id"]:
        payload[field] = _optional_int(payload.get(field))
    payload["public_visible"] = bool(payload.get("public_visible"))
