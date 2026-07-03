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
    "taxon_id",
    "geological_age_id",
    "locality_id",
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
    "preparation_type_id",
    "storage_location",
    "field_notes_links",
    "public_notes",
    "private_notes",
]

IMAGE_FIELDS = [
    "specimen_id",
    "image_path",
    "image_type",
    "caption",
    "photographer",
    "licence",
    "date_taken",
    "notes",
]

OBSERVATION_FIELDS = [
    "specimen_id",
    "observation_date",
    "observation_type",
    "notes",
    "related_project",
    "related_url",
]

TAXONOMY_FIELDS = [
    "kingdom",
    "phylum",
    "class_name",
    "order_name",
    "family",
    "genus",
    "species",
    "identification_confidence",
    "identification_notes",
]

LOCALITY_FIELDS = [
    "locality_name",
    "formation",
    "member",
    "region",
    "country",
    "latitude",
    "longitude",
    "locality_precision",
    "locality_notes",
]

GEOLOGICAL_AGE_FIELDS = [
    "era",
    "period",
    "epoch",
    "stage",
    "min_ma",
    "max_ma",
    "notes",
]

PREPARATION_TYPE_FIELDS = [
    "name",
    "description",
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
                OR source LIKE ?
            )"""
        )
        term = f"%{search.strip()}%"
        params.extend([term] * 14)

    if confidence != "All":
        clauses.append("ethical_confidence = ?")
        params.append(confidence)

    if documented_only:
        clauses.append("documentation_available = 1")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT specimens.*
        FROM specimens
        LEFT JOIN taxonomy ON taxonomy.id = specimens.taxon_id
        LEFT JOIN localities ON localities.id = specimens.locality_id
        LEFT JOIN geological_ages ON geological_ages.id = specimens.geological_age_id
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
    _coerce_specimen_foreign_keys(payload)
    payload["ethical_confidence"] = payload.get("ethical_confidence") or "Unknown"
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
    _coerce_specimen_foreign_keys(payload)
    payload["ethical_confidence"] = payload.get("ethical_confidence") or "Unknown"
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


def list_taxonomy(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List taxonomy records."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM taxonomy
                ORDER BY genus COLLATE NOCASE, species COLLATE NOCASE, identification_notes COLLATE NOCASE
                """
            )
        )


def get_taxonomy(taxon_id: int | None, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one taxonomy record."""

    if not taxon_id:
        return None
    with connect(db_path) as connection:
        return connection.execute("SELECT * FROM taxonomy WHERE id = ?", (taxon_id,)).fetchone()


def create_taxonomy(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a taxonomy record and return its id."""

    payload = _timestamped_payload(TAXONOMY_FIELDS, values)
    payload["identification_confidence"] = payload.get("identification_confidence") or "Unknown"
    return _insert_record("taxonomy", [*TAXONOMY_FIELDS, "created_at", "updated_at"], payload, db_path)


def list_localities(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List locality records."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM localities
                ORDER BY country COLLATE NOCASE, region COLLATE NOCASE, locality_name COLLATE NOCASE
                """
            )
        )


def get_locality(locality_id: int | None, db_path: Path | None = None) -> sqlite3.Row | None:
    """Fetch one locality record."""

    if not locality_id:
        return None
    with connect(db_path) as connection:
        return connection.execute("SELECT * FROM localities WHERE id = ?", (locality_id,)).fetchone()


def create_locality(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a locality record and return its id."""

    payload = _timestamped_payload(LOCALITY_FIELDS, values)
    payload["latitude"] = _optional_float(payload.get("latitude"))
    payload["longitude"] = _optional_float(payload.get("longitude"))
    return _insert_record("localities", [*LOCALITY_FIELDS, "created_at", "updated_at"], payload, db_path)


def list_geological_ages(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List geological age records."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM geological_ages
                ORDER BY max_ma DESC, min_ma DESC, period COLLATE NOCASE
                """
            )
        )


def get_geological_age(
    geological_age_id: int | None, db_path: Path | None = None
) -> sqlite3.Row | None:
    """Fetch one geological age record."""

    if not geological_age_id:
        return None
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM geological_ages WHERE id = ?", (geological_age_id,)
        ).fetchone()


def create_geological_age(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a geological age record and return its id."""

    payload = _timestamped_payload(GEOLOGICAL_AGE_FIELDS, values)
    payload["min_ma"] = _optional_float(payload.get("min_ma"))
    payload["max_ma"] = _optional_float(payload.get("max_ma"))
    return _insert_record(
        "geological_ages",
        [*GEOLOGICAL_AGE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def list_preparation_types(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List controlled preparation types."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM preparation_types
                ORDER BY name COLLATE NOCASE
                """
            )
        )


def create_preparation_type(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a preparation type and return its id."""

    payload = _timestamped_payload(PREPARATION_TYPE_FIELDS, values)
    return _insert_record(
        "preparation_types",
        [*PREPARATION_TYPE_FIELDS, "created_at", "updated_at"],
        payload,
        db_path,
    )


def list_specimen_images(
    specimen_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List images for one specimen."""

    with connect(db_path) as connection:
        return list(
            connection.execute(
                """
                SELECT *
                FROM specimen_images
                WHERE specimen_id = ?
                ORDER BY date_taken DESC, created_at DESC, id DESC
                """,
                (specimen_id,),
            )
        )


def create_specimen_image(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create an image record and return its id."""

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in IMAGE_FIELDS}
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
    """Update an image record."""

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in IMAGE_FIELDS}
    assignments = ", ".join([f"{field} = ?" for field in [*IMAGE_FIELDS, "updated_at"]])

    with connect(db_path) as connection:
        connection.execute(
            f"UPDATE specimen_images SET {assignments} WHERE id = ?",
            [payload[field] for field in IMAGE_FIELDS] + [now, image_id],
        )
        connection.commit()


def delete_specimen_image(image_id: int, db_path: Path | None = None) -> None:
    """Delete one image record."""

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimen_images WHERE id = ?", (image_id,))
        connection.commit()


def list_observations(
    specimen_id: int, db_path: Path | None = None
) -> list[sqlite3.Row]:
    """List observations for one specimen."""

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
    """Create an observation record and return its id."""

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
    """Update an observation record."""

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
    """Delete one observation record."""

    with connect(db_path) as connection:
        connection.execute("DELETE FROM observations WHERE id = ?", (observation_id,))
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
    orthocone_taxon_id = create_taxonomy(
        {
            "kingdom": "Animalia",
            "phylum": "Mollusca",
            "class_name": "Cephalopoda",
            "identification_confidence": "Unknown",
            "identification_notes": "Orthocone nautiloid, often sold as Orthoceras",
        },
        db_path,
    )
    stromatolite_taxon_id = create_taxonomy(
        {
            "identification_confidence": "Unknown",
            "identification_notes": "Microbialite, pending acquisition",
        },
        db_path,
    )
    madagascar_locality_id = create_locality(
        {
            "locality_name": "Exact locality unknown",
            "country": "Madagascar",
            "locality_precision": "Country only",
            "locality_notes": "Starter record. Replace with documented locality where possible.",
        },
        db_path,
    )
    morocco_locality_id = create_locality(
        {
            "locality_name": "Likely Morocco, exact locality unknown",
            "country": "Morocco",
            "locality_precision": "Country uncertain",
            "locality_notes": "Starter record. Verify seller documentation.",
        },
        db_path,
    )
    unknown_locality_id = create_locality(
        {
            "locality_name": "To be confirmed",
            "locality_precision": "Unknown",
        },
        db_path,
    )
    jurassic_age_id = _find_geological_age_id("Jurassic", db_path)
    palaeozoic_age_id = create_geological_age(
        {
            "era": "Palaeozoic",
            "notes": "Broad starter age record. Replace with a more precise period where possible.",
        },
        db_path,
    )
    split_polished_id = _find_preparation_type_id("Split and polished", db_path)
    polished_id = _find_preparation_type_id("Polished", db_path)

    starter_records: Iterable[dict[str, Any]] = [
        {
            "collection_code": "FT-0001",
            "title": "Split and polished Madagascan ammonite",
            "common_name": "Ammonite",
            "taxon_id": ammonite_taxon_id,
            "geological_age_id": jurassic_age_id,
            "locality_id": madagascar_locality_id,
            "source": "Unrecorded starter entry",
            "provenance_notes": "Seed record. Replace with the real acquisition source and documentation.",
            "legality_ethics_notes": "Unverified. Confirm export/import status and seller provenance.",
            "ethical_confidence": "Unknown",
            "documentation_available": False,
            "description": "Polished cross-section showing chamber structure.",
            "preparation_type_id": split_polished_id,
            "field_notes_links": "Shell morphology",
            "public_notes": "Candidate public summary once provenance is documented.",
        },
        {
            "collection_code": "FT-0002",
            "title": "Small polished Orthoceras fossil",
            "common_name": "Orthoceras",
            "taxon_id": orthocone_taxon_id,
            "geological_age_id": palaeozoic_age_id,
            "locality_id": morocco_locality_id,
            "source": "Unrecorded starter entry",
            "provenance_notes": "Seed record. Replace common trade label with documented details where possible.",
            "legality_ethics_notes": "Unverified. Confirm source and export documentation.",
            "ethical_confidence": "Unknown",
            "documentation_available": False,
            "description": "Small polished orthocone fossil suitable for morphology notes.",
            "preparation_type_id": polished_id,
            "field_notes_links": "Orthocone modelling",
        },
        {
            "collection_code": "FT-0003",
            "title": "Future stromatolite specimen",
            "common_name": "Stromatolite",
            "taxon_id": stromatolite_taxon_id,
            "locality_id": unknown_locality_id,
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
    if field in {"taxon_id", "geological_age_id", "locality_id", "preparation_type_id"}:
        return _optional_int(value)
    return value


def _timestamped_payload(fields: list[str], values: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = {field: values.get(field) for field in fields}
    payload["created_at"] = now
    payload["updated_at"] = now
    return payload


def _insert_record(
    table: str,
    fields: list[str],
    payload: dict[str, Any],
    db_path: Path | None = None,
) -> int:
    placeholders = ", ".join(["?"] * len(fields))
    with connect(db_path) as connection:
        cursor = connection.execute(
            f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})",
            [payload[field] for field in fields],
        )
        connection.commit()
        return int(cursor.lastrowid)


def _coerce_specimen_foreign_keys(payload: dict[str, Any]) -> None:
    for field in ["taxon_id", "geological_age_id", "locality_id", "preparation_type_id"]:
        payload[field] = _optional_int(payload.get(field))


def _find_geological_age_id(period: str, db_path: Path | None = None) -> int | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM geological_ages WHERE period = ? ORDER BY id LIMIT 1",
            (period,),
        ).fetchone()
    return int(row["id"]) if row else None


def _find_preparation_type_id(name: str, db_path: Path | None = None) -> int | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM preparation_types WHERE name = ? ORDER BY id LIMIT 1",
            (name,),
        ).fetchone()
    return int(row["id"]) if row else None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
