"""Specimen JSON export helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fossil_tracker.config import export_dir
from fossil_tracker.db import (
    get_acquisition,
    get_geological_age,
    get_locality,
    get_specimen,
    get_taxonomy,
    list_acquisition_documents,
    list_observations,
    list_related_links,
    list_specimen_images,
    list_specimen_measurements,
)


def export_specimen_json(specimen_id: int, db_path: Path) -> Path:
    """Export one specimen and linked tab data to JSON.

    :param specimen_id: Specimen primary key.
    :param db_path: SQLite database path.
    :return: Written JSON file path.
    """

    specimen = get_specimen(specimen_id, db_path)
    if specimen is None:
        raise ValueError("Specimen was not found.")

    output_dir = export_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / export_filename(specimen)
    output_path.write_text(
        json.dumps(build_specimen_export(specimen, db_path), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def build_specimen_export(specimen: dict, db_path: Path) -> dict[str, Any]:
    """Build the JSON-serializable specimen export payload."""

    taxon = get_taxonomy(specimen["taxon_id"], db_path)
    age = get_geological_age(specimen["geological_age_id"], db_path)
    locality = get_locality(specimen["locality_id"], db_path)
    acquisition = get_acquisition(specimen["acquisition_id"], db_path)

    specimen_data = export_dict(specimen)
    specimen_data["taxonomy"] = taxonomy_label(taxon)
    specimen_data["geological_age"] = geological_age_export(age)
    specimen_data["locality"] = locality_export(locality)
    specimen_data["acquisition"] = acquisition_label(acquisition)
    specimen_data["preparation_type"] = preparation_type_label(
        specimen["preparation_type_id"],
        db_path,
    )

    documents = []
    if acquisition:
        documents = [export_dict(document) for document in list_acquisition_documents(acquisition["id"], db_path)]

    images = [export_dict(image) for image in list_specimen_images(specimen["id"], db_path)]
    measurements = [
        measurement_export_row(measurement)
        for measurement in list_specimen_measurements(specimen["id"], db_path)
    ]

    return {
        "specimen": specimen_data,
        "taxonomy": export_dict(taxon) if taxon else None,
        "provenance": export_dict(acquisition) if acquisition else None,
        "documents": {"items": documents},
        "images": {"items": images},
        "notes": {"items": [export_dict(note) for note in list_observations(specimen["id"], db_path)]},
        "measurements": {"items": measurements},
        "related links": {
            "items": [export_dict(link) for link in list_related_links(specimen["id"], db_path)]
        },
    }


def row_dict(row: Any) -> dict[str, Any]:
    """Convert sqlite row-like values to plain dictionaries."""

    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}


def export_dict(row: Any) -> dict[str, Any]:
    """Convert a row to an export dictionary with internal ids removed."""

    return without_ids(row_dict(row))


def without_ids(values: dict[str, Any]) -> dict[str, Any]:
    """Remove primary and foreign key id fields from export dictionaries."""

    return {
        key: value
        for key, value in values.items()
        if key != "id" and not key.endswith("_id")
    }


def measurement_export_row(measurement: dict) -> dict[str, Any]:
    """Return one measurement row with reference display values."""

    values = export_dict(measurement)
    values["measurement_type"] = measurement["measurement_name"]
    return values


def taxonomy_label(taxon: dict | None) -> str | None:
    """Return the taxonomy display value used for specimen references."""

    if taxon is None:
        return None
    scientific_name = " ".join(part for part in [taxon["genus"], taxon["species"]] if part)
    higher_taxonomy = " > ".join(
        part
        for part in [
            taxon["kingdom"],
            taxon["phylum"],
            taxon["class_name"],
            taxon["order_name"],
            taxon["family"],
        ]
        if part
    )
    return scientific_name or taxon["identification_notes"] or higher_taxonomy or None


def geological_age_label(age: dict | None) -> str | None:
    """Return the geological age display value used for specimen references."""

    if age is None:
        return None
    return " / ".join(part for part in [age["period"], age["epoch"], age["stage"]] if part) or None


def geological_age_export(age: dict | None) -> dict[str, Any] | None:
    """Return geological age as a structured object for the specimen export."""

    if age is None:
        return None
    values = export_dict(age)
    return {
        field: values.get(field)
        for field in [
            "era",
            "period",
            "epoch",
            "stage",
            "min_ma",
            "max_ma",
        ]
    }


def locality_label(locality: dict | None) -> str | None:
    """Return the locality display value used for specimen references."""

    if locality is None:
        return None
    return ", ".join(
        part
        for part in [locality["locality_name"], locality["region"], locality["country"]]
        if part
    ) or None


def locality_export(locality: dict | None) -> dict[str, Any] | None:
    """Return locality as a structured object for the specimen export."""

    if locality is None:
        return None
    values = export_dict(locality)
    return {
        field: values.get(field)
        for field in [
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
    }


def acquisition_label(acquisition: dict | None) -> str | None:
    """Return the acquisition display value used for specimen references."""

    if acquisition is None:
        return None
    return " - ".join(
        part for part in [acquisition["acquisition_date"], acquisition["source_name"]] if part
    ) or None


def preparation_type_label(preparation_type_id: int | None, db_path: Path) -> str | None:
    """Return a preparation type display value for a specimen reference."""

    if not preparation_type_id:
        return None
    from fossil_tracker.db import list_preparation_types

    for preparation_type in list_preparation_types(db_path):
        if preparation_type["id"] == preparation_type_id:
            return preparation_type["name"]
    return None


def export_filename(specimen: dict) -> str:
    """Build a stable export filename for one specimen."""

    collection_code = safe_filename(specimen["collection_code"] or f"specimen-{specimen['id']}")
    return f"{collection_code}.json"


def safe_filename(value: str) -> str:
    """Convert a value into a filesystem-safe filename segment."""

    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip(".-")
    return cleaned or "specimen"
