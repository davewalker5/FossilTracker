"""Database access and schema management."""

from __future__ import annotations

import csv
import sqlite3
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
    "acquisition_id",
    "public_visible",
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

ACQUISITION_FIELDS = [
    "acquisition_date",
    "source_name",
    "source_type",
    "seller_url",
    "purchase_price",
    "currency",
    "provenance_summary",
    "legality_notes",
    "ethical_confidence",
    "notes",
]

ACQUISITION_DOCUMENT_FIELDS = [
    "acquisition_id",
    "document_path",
    "document_type",
    "title",
    "notes",
]


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row dictionaries and foreign keys enabled.

    :param db_path: Optional SQLite database path.
    :return: Configured SQLite connection.
    """

    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_migrations(db_path: Path | None = None) -> None:
    """Apply outstanding yoyo migrations to the configured database.

    :param db_path: Optional SQLite database path.
    """

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


def list_taxonomy(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List taxonomy records.

    :param db_path: Optional SQLite database path.
    :return: Taxonomy rows ordered for display.
    """

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
    """Fetch one taxonomy record.

    :param taxon_id: Taxonomy primary key.
    :param db_path: Optional SQLite database path.
    :return: Taxonomy row, or None when missing or unset.
    """

    if not taxon_id:
        return None
    with connect(db_path) as connection:
        return connection.execute("SELECT * FROM taxonomy WHERE id = ?", (taxon_id,)).fetchone()


def create_taxonomy(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a taxonomy record.

    :param values: Taxonomy field values.
    :param db_path: Optional SQLite database path.
    :return: New taxonomy id.
    """

    payload = _timestamped_payload(TAXONOMY_FIELDS, values)
    payload["identification_confidence"] = payload.get("identification_confidence") or "Unknown"
    return _insert_record("taxonomy", [*TAXONOMY_FIELDS, "created_at", "updated_at"], payload, db_path)


def list_localities(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List locality records.

    :param db_path: Optional SQLite database path.
    :return: Locality rows ordered for display.
    """

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
    """Fetch one locality record.

    :param locality_id: Locality primary key.
    :param db_path: Optional SQLite database path.
    :return: Locality row, or None when missing or unset.
    """

    if not locality_id:
        return None
    with connect(db_path) as connection:
        return connection.execute("SELECT * FROM localities WHERE id = ?", (locality_id,)).fetchone()


def create_locality(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a locality record.

    :param values: Locality field values.
    :param db_path: Optional SQLite database path.
    :return: New locality id.
    """

    payload = _timestamped_payload(LOCALITY_FIELDS, values)
    payload["latitude"] = _optional_float(payload.get("latitude"))
    payload["longitude"] = _optional_float(payload.get("longitude"))
    return _insert_record("localities", [*LOCALITY_FIELDS, "created_at", "updated_at"], payload, db_path)


def list_geological_ages(db_path: Path | None = None) -> list[sqlite3.Row]:
    """List geological age records.

    :param db_path: Optional SQLite database path.
    :return: Geological age rows ordered for display.
    """

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
    """Fetch one geological age record.

    :param geological_age_id: Geological age primary key.
    :param db_path: Optional SQLite database path.
    :return: Geological age row, or None when missing or unset.
    """

    if not geological_age_id:
        return None
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT * FROM geological_ages WHERE id = ?", (geological_age_id,)
        ).fetchone()


def create_geological_age(values: dict[str, Any], db_path: Path | None = None) -> int:
    """Create a geological age record.

    :param values: Geological age field values.
    :param db_path: Optional SQLite database path.
    :return: New geological age id.
    """

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
    """List controlled preparation types.

    :param db_path: Optional SQLite database path.
    :return: Preparation type rows ordered for display.
    """

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
    """Create a preparation type.

    :param values: Preparation type field values.
    :param db_path: Optional SQLite database path.
    :return: New preparation type id.
    """

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
    """List images for one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: Optional SQLite database path.
    :return: Image rows linked to the specimen.
    """

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
    """Create an image record.

    :param values: Image field values.
    :param db_path: Optional SQLite database path.
    :return: New image id.
    """

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
    """Update an image record.

    :param image_id: Image primary key.
    :param values: Image field values.
    :param db_path: Optional SQLite database path.
    """

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
    """Delete one image record.

    :param image_id: Image primary key.
    :param db_path: Optional SQLite database path.
    """

    with connect(db_path) as connection:
        connection.execute("DELETE FROM specimen_images WHERE id = ?", (image_id,))
        connection.commit()


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


def export_csv(destination: Path, db_path: Path | None = None) -> None:
    """Export the register to CSV for long-term portability.

    :param destination: CSV file path to write.
    :param db_path: Optional SQLite database path.
    """

    rows = list_specimens(db_path=db_path)
    fieldnames = ["id", *SPECIMEN_FIELDS, "created_at", "updated_at"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fieldnames})


def import_csv(source: Path, db_path: Path | None = None) -> int:
    """Import specimen rows from a CSV file created by Fossil Tracker.

    :param source: CSV file path to read.
    :param db_path: Optional SQLite database path.
    :return: Number of imported specimens.
    """

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
            "locality_notes": "Starter record. Replace with documented locality where possible.",
        },
        db_path,
    )
    jurassic_age_id = _find_geological_age_id("Jurassic", db_path)
    split_polished_id = _find_preparation_type_id("Split and polished", db_path)
    ammonite_acquisition_id = create_acquisition(
        {
            "source_name": "Unrecorded starter entry",
            "provenance_summary": "Seed record. Replace with the real acquisition source and documentation.",
            "legality_notes": "Unverified. Confirm export/import status and seller provenance.",
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
            "field_notes_links": "Shell morphology",
            "public_notes": "Candidate public summary once provenance is documented.",
        },
        db_path=db_path,
    )
    return 1


def _coerce_csv_value(field: str, value: str | None) -> Any:
    """Convert a CSV string value into the type expected for a specimen field.

    :param field: Specimen field name.
    :param value: Raw CSV value.
    :return: Coerced value for database insertion.
    """

    if field == "public_visible":
        return str(value).strip().lower() in {"1", "true", "yes", "y"}
    if field in {"taxon_id", "geological_age_id", "locality_id", "preparation_type_id", "acquisition_id"}:
        return _optional_int(value)
    return value


def _timestamped_payload(fields: list[str], values: dict[str, Any]) -> dict[str, Any]:
    """Build an insert payload with created and updated timestamps.

    :param fields: Field names to copy from values.
    :param values: Input values.
    :return: Payload dictionary including timestamps.
    """

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
    """Insert one row into a table.

    :param table: Target table name.
    :param fields: Ordered field names to insert.
    :param payload: Values keyed by field name.
    :param db_path: Optional SQLite database path.
    :return: New record id.
    """

    placeholders = ", ".join(["?"] * len(fields))
    with connect(db_path) as connection:
        cursor = connection.execute(
            f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})",
            [payload[field] for field in fields],
        )
        record_id = int(cursor.lastrowid)
        connection.commit()
    return record_id


def _coerce_specimen_foreign_keys(payload: dict[str, Any]) -> None:
    """Normalize specimen foreign-key and boolean values in place.

    :param payload: Specimen insert/update payload.
    """

    for field in ["taxon_id", "geological_age_id", "locality_id", "preparation_type_id", "acquisition_id"]:
        payload[field] = _optional_int(payload.get(field))
    payload["public_visible"] = bool(payload.get("public_visible"))


def _find_geological_age_id(period: str, db_path: Path | None = None) -> int | None:
    """Find the first geological age id for a period.

    :param period: Geological period name.
    :param db_path: Optional SQLite database path.
    :return: Geological age id, or None when missing.
    """

    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM geological_ages WHERE period = ? ORDER BY id LIMIT 1",
            (period,),
        ).fetchone()
    return int(row["id"]) if row else None


def _find_preparation_type_id(name: str, db_path: Path | None = None) -> int | None:
    """Find the first preparation type id by name.

    :param name: Preparation type name.
    :param db_path: Optional SQLite database path.
    :return: Preparation type id, or None when missing.
    """

    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM preparation_types WHERE name = ? ORDER BY id LIMIT 1",
            (name,),
        ).fetchone()
    return int(row["id"]) if row else None


def _optional_int(value: Any) -> int | None:
    """Convert an optional value to an integer.

    :param value: Raw value.
    :return: Integer value, or None when blank.
    """

    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    """Convert an optional value to a float.

    :param value: Raw value.
    :return: Float value, or None when blank.
    """

    if value is None or value == "":
        return None
    return float(value)
