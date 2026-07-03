"""Database access and schema management."""

from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import MIGRATIONS_PATH, database_path

SPECIMEN_FIELDS = [
    "collection_code",
    "title",
    "common_name",
    "taxonomic_identification",
    "geological_age",
    "formation_or_locality",
    "country_region",
    "acquisition_date",
    "source",
    "purchase_price",
    "currency",
    "provenance_notes",
    "legality_ethics_notes",
    "ethical_confidence",
    "documentation_available",
    "description",
    "measurements",
    "preparation_type",
    "storage_location",
    "image_paths",
    "field_notes_links",
    "public_notes",
    "private_notes",
]


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row dictionaries and foreign keys enabled."""

    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_migrations(db_path: Path | None = None) -> None:
    """Apply outstanding yoyo migrations to the configured database."""

    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from yoyo import get_backend, read_migrations
    except ImportError as exc:
        raise RuntimeError(
            "yoyo-migrations is required to initialise the database. "
            "Install the project dependencies with `pip install -e .`."
        ) from exc

    backend = get_backend(f"sqlite:///{path}")
    migrations = read_migrations(str(MIGRATIONS_PATH))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def specimen_count(db_path: Path | None = None) -> int:
    """Return the number of registered specimens."""

    with connect(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM specimens").fetchone()
    return int(row["count"])


def list_specimens(
    db_path: Path | None = None,
    search: str = "",
    confidence: str = "All",
    documented_only: bool = False,
) -> list[sqlite3.Row]:
    """List specimens with simple filters for the Streamlit register view."""

    clauses: list[str] = []
    params: list[Any] = []

    if search.strip():
        clauses.append(
            """(
                collection_code LIKE ?
                OR title LIKE ?
                OR common_name LIKE ?
                OR taxonomic_identification LIKE ?
                OR formation_or_locality LIKE ?
                OR country_region LIKE ?
                OR source LIKE ?
            )"""
        )
        term = f"%{search.strip()}%"
        params.extend([term] * 7)

    if confidence != "All":
        clauses.append("ethical_confidence = ?")
        params.append(confidence)

    if documented_only:
        clauses.append("documentation_available = 1")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT *
        FROM specimens
        {where}
        ORDER BY collection_code COLLATE NOCASE, created_at DESC
    """

    with connect(db_path) as connection:
        return list(connection.execute(sql, params))


def get_specimen(specimen_id: int, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one specimen by id."""

    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM specimens WHERE id = ?", (specimen_id,)
        ).fetchone()


def create_specimen(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a specimen and return its id."""

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in SPECIMEN_FIELDS}
    payload["documentation_available"] = bool(payload.get("documentation_available"))
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
    """Update the editable fields for a specimen."""

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in SPECIMEN_FIELDS}
    payload["documentation_available"] = bool(payload.get("documentation_available"))
    payload["updated_at"] = now
    assignments = ", ".join([f"{field} = ?" for field in [*SPECIMEN_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE specimens SET {assignments} WHERE id = ?",
            [payload[field] for field in SPECIMEN_FIELDS] + [now, specimen_id],
        )
        connection.commit()


def delete_specimen(specimen_id: int, db_path: Path | None = None) -> None:
    """Delete one specimen."""

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimens WHERE id = ?", (specimen_id,))
        connection.commit()


def export_csv(destination: Path, db_path: Path | None = None) -> None:
    """Export the register to CSV for long-term portability."""

    rows = list_specimens(db_path=db_path)
    fieldnames = ["id", *SPECIMEN_FIELDS, "created_at", "updated_at"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fieldnames})


def import_csv(source: Path, db_path: Path | None = None) -> int:
    """Import specimen rows from a CSV file created by Fossil Tracker."""

    count = 0
    with source.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            create_specimen(
                {
                    field: _coerce_csv_value(field, row.get(field))
                    for field in SPECIMEN_FIELDS
                },
                db_path=db_path,
            )
            count += 1
    return count


def seed_specimens(db_path: Path | None = None) -> int:
    """Create the three suggested starter records when the register is empty."""

    if specimen_count(db_path) > 0:
        return 0

    starter_records: Iterable[dict[str, Any]] = [
        {
            "collection_code": "FT-0001",
            "title": "Split and polished Madagascan ammonite",
            "common_name": "Ammonite",
            "taxonomic_identification": "Ammonoidea, identification pending",
            "geological_age": "Jurassic or Cretaceous, verify with seller documentation",
            "formation_or_locality": "Madagascar, exact locality unknown",
            "country_region": "Madagascar",
            "source": "Unrecorded starter entry",
            "provenance_notes": "Seed record. Replace with the real acquisition source and documentation.",
            "legality_ethics_notes": "Unverified. Confirm export/import status and seller provenance.",
            "ethical_confidence": "Unknown",
            "documentation_available": False,
            "description": "Polished cross-section showing chamber structure.",
            "preparation_type": "Split and polished",
            "field_notes_links": "Shell morphology",
            "public_notes": "Candidate public summary once provenance is documented.",
        },
        {
            "collection_code": "FT-0002",
            "title": "Small polished Orthoceras fossil",
            "common_name": "Orthoceras",
            "taxonomic_identification": "Orthocone nautiloid, often sold as Orthoceras",
            "geological_age": "Palaeozoic, verify exact age",
            "formation_or_locality": "Likely Morocco, exact locality unknown",
            "country_region": "Morocco",
            "source": "Unrecorded starter entry",
            "provenance_notes": "Seed record. Replace common trade label with documented details where possible.",
            "legality_ethics_notes": "Unverified. Confirm source and export documentation.",
            "ethical_confidence": "Unknown",
            "documentation_available": False,
            "description": "Small polished orthocone fossil suitable for morphology notes.",
            "preparation_type": "Polished",
            "field_notes_links": "Orthocone modelling",
        },
        {
            "collection_code": "FT-0003",
            "title": "Future stromatolite specimen",
            "common_name": "Stromatolite",
            "taxonomic_identification": "Microbialite, pending acquisition",
            "geological_age": "To be confirmed",
            "formation_or_locality": "To be confirmed",
            "source": "Placeholder",
            "provenance_notes": "Only acquire if a genuine, well-documented, ethical specimen is found.",
            "legality_ethics_notes": "Acquisition not yet made.",
            "ethical_confidence": "Unknown",
            "documentation_available": False,
            "description": "Placeholder connecting the register to stromatolite growth modelling.",
            "field_notes_links": "Stromatolite growth modelling",
        },
    ]

    for record in starter_records:
        create_specimen(record, db_path=db_path)
    return len(list(starter_records))


def _coerce_csv_value(field: str, value: str | None) -> Any:
    if field == "documentation_available":
        return str(value).strip().lower() in {"1", "true", "yes", "y"}
    return value
