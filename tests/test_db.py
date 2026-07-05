from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from fossil_tracker import db
from ui.specimen_export import export_specimen_json


SCHEMA = """
CREATE TABLE specimens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    common_name TEXT,
    taxon_id INTEGER,
    geological_age_id INTEGER,
    locality_id INTEGER,
    acquisition_id INTEGER,
    public_visible INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    preparation_type_id INTEGER,
    storage_location TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE taxonomy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kingdom TEXT,
    phylum TEXT,
    class_name TEXT,
    subclass TEXT,
    order_name TEXT,
    family TEXT,
    genus TEXT,
    species TEXT,
    identification_confidence TEXT NOT NULL DEFAULT 'Unknown',
    identification_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE localities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    locality_name TEXT,
    formation TEXT,
    member TEXT,
    region TEXT,
    country TEXT,
    latitude REAL,
    longitude REAL,
    locality_precision TEXT,
    locality_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE geological_ages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    era TEXT,
    period TEXT,
    epoch TEXT,
    stage TEXT,
    min_ma REAL,
    max_ma REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE preparation_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE licences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    notes TEXT,
    url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE measurement_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    unit TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE image_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE document_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE acquisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acquisition_date TEXT,
    source_name TEXT,
    source_type TEXT,
    seller_url TEXT,
    purchase_price TEXT,
    currency TEXT,
    provenance_summary TEXT,
    legality_notes TEXT,
    ethical_confidence TEXT NOT NULL DEFAULT 'Unknown',
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE acquisition_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acquisition_id INTEGER NOT NULL,
    document_path TEXT NOT NULL,
    document_type_id INTEGER,
    title TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (acquisition_id) REFERENCES acquisitions (id) ON DELETE CASCADE,
    FOREIGN KEY (document_type_id) REFERENCES document_types (id)
);

CREATE TABLE specimen_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    image_type_id INTEGER,
    caption TEXT,
    photographer TEXT,
    licence TEXT,
    date_taken TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE,
    FOREIGN KEY (image_type_id) REFERENCES image_types (id)
);

CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    observation_date TEXT,
    observation_type TEXT,
    notes TEXT NOT NULL,
    public_visible INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
);

CREATE TABLE specimen_related_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
);

CREATE TABLE specimen_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    measurement_type_id INTEGER NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE,
    FOREIGN KEY (measurement_type_id) REFERENCES measurement_types (id),
    UNIQUE (specimen_id, measurement_type_id)
);

CREATE UNIQUE INDEX idx_specimens_taxon_id_unique
ON specimens (taxon_id)
WHERE taxon_id IS NOT NULL;
"""


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
    return path


def test_create_and_filter_specimen(db_path: Path) -> None:
    taxon_id = db.create_taxonomy(
        {
            "identification_notes": "Ammonoidea",
            "identification_confidence": "High",
        },
        db_path,
    )
    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-1000",
            "title": "Test ammonite",
            "taxon_id": taxon_id,
        },
        db_path,
    )

    specimen = db.get_specimen(specimen_id, db_path)
    assert specimen is not None
    assert specimen["collection_code"] == "FT-1000"

    filtered = db.list_specimens(db_path, search="ammonite")
    assert len(filtered) == 1


def test_next_collection_code_uses_next_ft_number(db_path: Path) -> None:
    assert db.next_collection_code(db_path) == "FT-0001"

    db.create_specimen(
        {
            "collection_code": "FT-0001",
            "title": "First specimen",
        },
        db_path,
    )
    db.create_specimen(
        {
            "collection_code": "FT-0010",
            "title": "Tenth specimen",
        },
        db_path,
    )
    db.create_specimen(
        {
            "collection_code": "OTHER-9999",
            "title": "Other collection",
        },
        db_path,
    )

    assert db.next_collection_code(db_path) == "FT-0011"


def test_seed_only_when_empty(db_path: Path) -> None:
    assert db.seed_specimens(db_path) == 1
    assert db.seed_specimens(db_path) == 0
    assert db.specimen_count(db_path) == 1


def test_create_image_and_observation_records(db_path: Path) -> None:
    overall_type_id = db.create_image_type({"name": "Overall"}, db_path)
    closeup_type_id = db.create_image_type({"name": "Close-up"}, db_path)
    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-2000",
            "title": "Image and notes test",
        },
        db_path,
    )

    image_id = db.create_specimen_image(
        {
            "specimen_id": specimen_id,
            "image_path": "data/images/FT-2000.jpg",
            "image_type_id": overall_type_id,
            "caption": "Overall view",
            "photographer": "D. Walker",
            "licence": "Private",
            "date_taken": "2026-07-03",
            "notes": "Shows the complete specimen.",
        },
        db_path,
    )
    observation_id = db.create_observation(
        {
            "specimen_id": specimen_id,
            "observation_date": "2026-07-03",
            "observation_type": "Morphology",
            "notes": "**Markdown** observation note.",
            "public_visible": True,
        },
        db_path,
    )

    images = db.list_specimen_images(specimen_id, db_path)
    observations = db.list_observations(specimen_id, db_path)
    assert len(images) == 1
    assert images[0]["id"] == image_id
    assert images[0]["caption"] == "Overall view"
    db.update_specimen_image(
        image_id,
        {
            "specimen_id": specimen_id,
            "image_path": "data/images/FT-2000.jpg",
            "image_type_id": closeup_type_id,
            "caption": "Updated close-up",
            "photographer": "D. Walker",
            "licence": "CC BY 4.0",
            "date_taken": "2026-07-04",
            "notes": "Updated image notes.",
        },
        db_path,
    )
    updated_images = db.list_specimen_images(specimen_id, db_path)
    assert updated_images[0]["caption"] == "Updated close-up"
    assert updated_images[0]["image_type"] == "Close-up"
    assert updated_images[0]["image_type_id"] == closeup_type_id
    assert updated_images[0]["licence"] == "CC BY 4.0"
    assert len(observations) == 1
    assert observations[0]["id"] == observation_id
    assert observations[0]["notes"] == "**Markdown** observation note."
    assert observations[0]["public_visible"] == 1

    db.delete_specimen_image(image_id, db_path)
    db.delete_observation(observation_id, db_path)
    assert db.list_specimen_images(specimen_id, db_path) == []
    assert db.list_observations(specimen_id, db_path) == []


def test_create_related_links_and_cascade_delete(db_path: Path) -> None:
    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-2500",
            "title": "Related links test",
        },
        db_path,
    )
    first_link_id = db.create_related_link(
        {
            "specimen_id": specimen_id,
            "url": "https://fieldnotes.example/first",
            "title": "First field note",
            "description": "Primary contextual resource.",
        },
        db_path,
    )
    db.create_related_link(
        {
            "specimen_id": specimen_id,
            "url": "https://fieldnotes.example/second",
        },
        db_path,
    )

    links = db.list_related_links(specimen_id, db_path)
    assert len(links) == 2
    assert links[1]["id"] == first_link_id
    assert links[1]["url"] == "https://fieldnotes.example/first"
    assert links[1]["title"] == "First field note"
    assert links[1]["description"] == "Primary contextual resource."

    db.update_related_link(
        first_link_id,
        {
            "specimen_id": specimen_id,
            "url": "https://fieldnotes.example/first-updated",
            "title": "Updated field note",
            "description": "Updated contextual resource.",
        },
        db_path,
    )
    links = db.list_related_links(specimen_id, db_path)
    updated_link = next(link for link in links if link["id"] == first_link_id)
    assert updated_link["url"] == "https://fieldnotes.example/first-updated"
    assert updated_link["title"] == "Updated field note"
    assert updated_link["description"] == "Updated contextual resource."

    db.delete_related_link(first_link_id, db_path)
    links = db.list_related_links(specimen_id, db_path)
    assert len(links) == 1
    assert links[0]["url"] == "https://fieldnotes.example/second"

    db.delete_specimen(specimen_id, db_path)
    assert db.list_related_links(specimen_id, db_path) == []


def test_create_context_records_and_link_specimen(db_path: Path) -> None:
    taxon_id = db.create_taxonomy(
        {
            "kingdom": "Animalia",
            "phylum": "Mollusca",
            "class_name": "Cephalopoda",
            "subclass": "Ammonoidea",
            "genus": "Dactylioceras",
            "species": "commune",
            "identification_confidence": "Medium",
        },
        db_path,
    )
    age_id = db.create_geological_age(
        {
            "era": "Mesozoic",
            "period": "Jurassic",
            "epoch": "Early Jurassic",
            "max_ma": "201.4",
            "min_ma": "174.7",
        },
        db_path,
    )
    locality_id = db.create_locality(
        {
            "locality_name": "Whitby",
            "formation": "Whitby Mudstone Formation",
            "region": "North Yorkshire",
            "country": "England",
            "latitude": "54.486",
            "longitude": "-0.614",
        },
        db_path,
    )
    preparation_type_id = db.create_preparation_type(
        {"name": "Prepared", "description": "Prepared specimen."},
        db_path,
    )

    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-3000",
            "title": "Context specimen",
            "taxon_id": taxon_id,
            "geological_age_id": age_id,
            "locality_id": locality_id,
            "preparation_type_id": preparation_type_id,
        },
        db_path,
    )

    specimen = db.get_specimen(specimen_id, db_path)
    assert specimen["taxon_id"] == taxon_id
    assert specimen["geological_age_id"] == age_id
    assert specimen["locality_id"] == locality_id
    assert specimen["preparation_type_id"] == preparation_type_id
    assert db.get_taxonomy(taxon_id, db_path)["genus"] == "Dactylioceras"
    assert db.get_taxonomy(taxon_id, db_path)["subclass"] == "Ammonoidea"
    assert db.get_taxonomy_for_specimen(specimen_id, db_path)["id"] == taxon_id
    assert db.get_geological_age(age_id, db_path)["period"] == "Jurassic"
    assert db.get_locality(locality_id, db_path)["country"] == "England"

    db.update_taxonomy(
        taxon_id,
        {
            "kingdom": "Animalia",
            "phylum": "Mollusca",
            "class_name": "Cephalopoda",
            "subclass": "Ammonoidea",
            "genus": "Hildoceras",
            "species": "bifrons",
            "identification_confidence": "High",
        },
        db_path,
    )
    db.update_geological_age(
        age_id,
        {
            "era": "Mesozoic",
            "period": "Jurassic",
            "epoch": "Early Jurassic",
            "max_ma": "201.4",
            "min_ma": "174.7",
        },
        db_path,
    )
    db.update_locality(
        locality_id,
        {
            "locality_name": "Charmouth",
            "formation": "Charmouth Mudstone Formation",
            "region": "Dorset",
            "country": "England",
            "latitude": "50.738",
            "longitude": "-2.902",
        },
        db_path,
    )
    db.update_preparation_type(
        preparation_type_id,
        {"name": "Prepared and stabilized", "description": "Updated preparation."},
        db_path,
    )

    assert db.get_taxonomy(taxon_id, db_path)["genus"] == "Hildoceras"
    assert db.get_geological_age(age_id, db_path)["period"] == "Jurassic"
    assert db.get_locality(locality_id, db_path)["locality_name"] == "Charmouth"
    preparation_names = [row["name"] for row in db.list_preparation_types(db_path)]
    assert "Prepared and stabilized" in preparation_names


def test_taxonomy_record_can_only_be_linked_to_one_specimen(db_path: Path) -> None:
    taxon_id = db.create_taxonomy({"genus": "Dactylioceras"}, db_path)
    db.create_specimen(
        {
            "collection_code": "FT-3100",
            "title": "First taxonomy specimen",
            "taxon_id": taxon_id,
        },
        db_path,
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.create_specimen(
            {
                "collection_code": "FT-3101",
                "title": "Second taxonomy specimen",
                "taxon_id": taxon_id,
            },
            db_path,
        )


def test_delete_context_records(db_path: Path) -> None:
    taxon_id = db.create_taxonomy({"identification_notes": "Temporary taxon"}, db_path)
    age_id = db.create_geological_age({"period": "Temporary period"}, db_path)
    locality_id = db.create_locality({"locality_name": "Temporary locality"}, db_path)
    preparation_type_id = db.create_preparation_type(
        {"name": "Temporary preparation"},
        db_path,
    )

    db.delete_taxonomy(taxon_id, db_path)
    db.delete_geological_age(age_id, db_path)
    db.delete_locality(locality_id, db_path)
    db.delete_preparation_type(preparation_type_id, db_path)

    assert db.get_taxonomy(taxon_id, db_path) is None
    assert db.get_geological_age(age_id, db_path) is None
    assert db.get_locality(locality_id, db_path) is None
    assert preparation_type_id not in [row["id"] for row in db.list_preparation_types(db_path)]


def test_create_update_and_delete_measurement_type(db_path: Path) -> None:
    measurement_type_id = db.create_measurement_type(
        {
            "name": "Umbilicus Diameter",
            "unit": "mm",
            "description": "Ammonite umbilicus diameter.",
        },
        db_path,
    )

    measurement_type = db.get_measurement_type(measurement_type_id, db_path)
    assert measurement_type["name"] == "Umbilicus Diameter"
    assert measurement_type["unit"] == "mm"

    db.update_measurement_type(
        measurement_type_id,
        {
            "name": "Umbilicus Width",
            "unit": "mm",
            "description": "Updated description.",
        },
        db_path,
    )
    updated = db.get_measurement_type(measurement_type_id, db_path)
    assert updated["name"] == "Umbilicus Width"
    assert updated["description"] == "Updated description."

    measurement_types = db.list_measurement_types(db_path)
    assert [row["id"] for row in measurement_types] == [measurement_type_id]

    db.delete_measurement_type(measurement_type_id, db_path)
    assert db.list_measurement_types(db_path) == []


def test_create_update_and_delete_image_type(db_path: Path) -> None:
    image_type_id = db.create_image_type(
        {"name": "Macro", "description": "Detailed macro image."},
        db_path,
    )

    image_types = db.list_image_types(db_path)
    assert [row["id"] for row in image_types] == [image_type_id]
    assert image_types[0]["name"] == "Macro"

    db.update_image_type(
        image_type_id,
        {"name": "Macro detail", "description": "Updated description."},
        db_path,
    )
    updated = db.list_image_types(db_path)
    assert updated[0]["name"] == "Macro detail"
    assert updated[0]["description"] == "Updated description."

    db.delete_image_type(image_type_id, db_path)
    assert db.list_image_types(db_path) == []


def test_create_update_and_delete_document_type(db_path: Path) -> None:
    document_type_id = db.create_document_type(
        {"name": "Permit", "description": "Export permit."},
        db_path,
    )

    document_types = db.list_document_types(db_path)
    assert [row["id"] for row in document_types] == [document_type_id]
    assert document_types[0]["name"] == "Permit"

    db.update_document_type(
        document_type_id,
        {"name": "Export Permit", "description": "Updated description."},
        db_path,
    )
    updated = db.list_document_types(db_path)
    assert updated[0]["name"] == "Export Permit"
    assert updated[0]["description"] == "Updated description."

    db.delete_document_type(document_type_id, db_path)
    assert db.list_document_types(db_path) == []


def test_create_update_and_delete_licence(db_path: Path) -> None:
    licence_id = db.create_licence(
        {
            "name": "CC BY 4.0",
            "notes": "Attribution required.",
            "url": "https://creativecommons.org/licenses/by/4.0/",
        },
        db_path,
    )

    licence = db.get_licence(licence_id, db_path)
    assert licence["name"] == "CC BY 4.0"
    assert licence["url"] == "https://creativecommons.org/licenses/by/4.0/"

    db.update_licence(
        licence_id,
        {
            "name": "CC BY-SA 4.0",
            "notes": "Attribution and share-alike required.",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
        db_path,
    )
    updated = db.get_licence(licence_id, db_path)
    assert updated["name"] == "CC BY-SA 4.0"
    assert updated["notes"] == "Attribution and share-alike required."

    licences = db.list_licences(db_path)
    assert [row["id"] for row in licences] == [licence_id]

    db.delete_licence(licence_id, db_path)
    assert db.get_licence(licence_id, db_path) is None
    assert db.list_licences(db_path) == []


def test_licence_name_is_unique_case_insensitive(db_path: Path) -> None:
    db.create_licence({"name": "CC0"}, db_path)
    with pytest.raises(sqlite3.IntegrityError):
        db.create_licence({"name": "cc0"}, db_path)


def test_measurement_type_name_is_unique_case_insensitive(db_path: Path) -> None:
    db.create_measurement_type({"name": "Length", "unit": "mm"}, db_path)
    with pytest.raises(sqlite3.IntegrityError):
        db.create_measurement_type({"name": "length", "unit": "mm"}, db_path)


def test_create_specimen_measurements_and_cascade_delete(db_path: Path) -> None:
    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-3500",
            "title": "Measured specimen",
        },
        db_path,
    )
    measurement_type_id = db.create_measurement_type(
        {
            "name": "Length",
            "unit": "mm",
        },
        db_path,
    )
    measurement_id = db.create_specimen_measurement(
        {
            "specimen_id": specimen_id,
            "measurement_type_id": measurement_type_id,
            "value": "43.2",
        },
        db_path,
    )

    measurements = db.list_specimen_measurements(specimen_id, db_path)
    assert len(measurements) == 1
    assert measurements[0]["id"] == measurement_id
    assert measurements[0]["measurement_name"] == "Length"
    assert measurements[0]["measurement_unit"] == "mm"
    assert measurements[0]["value"] == "43.2"

    with pytest.raises(sqlite3.IntegrityError):
        db.create_specimen_measurement(
            {
                "specimen_id": specimen_id,
                "measurement_type_id": measurement_type_id,
                "value": "44.0",
            },
            db_path,
        )

    db.delete_specimen_measurement(measurement_id, db_path)
    assert db.list_specimen_measurements(specimen_id, db_path) == []

    measurement_id = db.create_specimen_measurement(
        {
            "specimen_id": specimen_id,
            "measurement_type_id": measurement_type_id,
            "value": "43.2",
        },
        db_path,
    )
    assert isinstance(measurement_id, int)
    db.delete_specimen(specimen_id, db_path)
    assert db.list_specimen_measurements(specimen_id, db_path) == []


def test_create_acquisition_and_document_records(db_path: Path) -> None:
    receipt_type_id = db.create_document_type({"name": "Acquisition Receipt"}, db_path)
    paper_type_id = db.create_document_type({"name": "Scientific Paper"}, db_path)
    acquisition_id = db.create_acquisition(
        {
            "acquisition_date": "2026-07-03",
            "source_name": "Example dealer",
            "source_type": "Seller",
            "purchase_price": "25.00",
            "currency": "GBP",
            "provenance_summary": "Documented purchase.",
            "legality_notes": "Export status documented.",
            "ethical_confidence": "High",
        },
        db_path,
    )
    document_id = db.create_acquisition_document(
        {
            "acquisition_id": acquisition_id,
            "document_path": "data/documents/receipt.pdf",
            "document_type_id": receipt_type_id,
            "title": "Purchase receipt",
        },
        db_path,
    )
    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-4000",
            "title": "Provenance specimen",
            "acquisition_id": acquisition_id,
            "public_visible": True,
        },
        db_path,
    )

    acquisition = db.get_acquisition(acquisition_id, db_path)
    specimen = db.get_specimen(specimen_id, db_path)
    documents = db.list_acquisition_documents(acquisition_id, db_path)
    assert acquisition["source_name"] == "Example dealer"
    assert db.has_acquisition_documents(acquisition_id, db_path)
    assert specimen["acquisition_id"] == acquisition_id
    assert specimen["public_visible"] == 1
    assert documents[0]["id"] == document_id
    assert documents[0]["title"] == "Purchase receipt"
    assert documents[0]["document_type"] == "Acquisition Receipt"
    assert documents[0]["document_type_id"] == receipt_type_id
    filtered = db.list_specimens(db_path, documented_only=True)
    assert [row["id"] for row in filtered] == [specimen_id]

    db.update_acquisition_document(
        document_id,
        {
            "acquisition_id": acquisition_id,
            "document_path": "receipt.pdf",
            "document_type_id": paper_type_id,
            "title": "Updated purchase receipt",
            "notes": "Updated document notes.",
        },
        db_path,
    )
    documents = db.list_acquisition_documents(acquisition_id, db_path)
    assert documents[0]["document_path"] == "receipt.pdf"
    assert documents[0]["document_type"] == "Scientific Paper"
    assert documents[0]["document_type_id"] == paper_type_id
    assert documents[0]["title"] == "Updated purchase receipt"
    assert documents[0]["notes"] == "Updated document notes."

    db.update_acquisition(
        acquisition_id,
        {
            "acquisition_date": "2026-07-04",
            "source_name": "Updated dealer",
            "source_type": "Auction",
            "purchase_price": "30.00",
            "currency": "GBP",
            "provenance_summary": "Updated purchase record.",
            "legality_notes": "Updated export status.",
            "ethical_confidence": "Medium",
            "notes": "Updated private note.",
        },
        db_path,
    )
    updated = db.get_acquisition(acquisition_id, db_path)
    assert updated["source_name"] == "Updated dealer"
    assert updated["source_type"] == "Auction"
    assert updated["ethical_confidence"] == "Medium"


def test_export_specimen_json_writes_tabbed_payload(
    db_path: Path, tmp_path: Path, monkeypatch
) -> None:
    export_folder = tmp_path / "exports"
    monkeypatch.setenv("FOSSIL_TRACKER_EXPORT", str(export_folder))

    taxon_id = db.create_taxonomy({"genus": "Dactylioceras", "species": "commune"}, db_path)
    age_id = db.create_geological_age({"period": "Jurassic", "epoch": "Early Jurassic"}, db_path)
    locality_id = db.create_locality(
        {"locality_name": "Charmouth", "region": "Dorset", "country": "England"},
        db_path,
    )
    preparation_type_id = db.create_preparation_type({"name": "Prepared"}, db_path)
    acquisition_id = db.create_acquisition(
        {"acquisition_date": "2026-07-03", "source_name": "Example dealer"},
        db_path,
    )
    image_type_id = db.create_image_type({"name": "Overall"}, db_path)
    document_type_id = db.create_document_type({"name": "Acquisition Receipt"}, db_path)
    measurement_type_id = db.create_measurement_type({"name": "Length", "unit": "mm"}, db_path)
    specimen_id = db.create_specimen(
        {
            "collection_code": "FT-9000",
            "title": "Export specimen",
            "taxon_id": taxon_id,
            "geological_age_id": age_id,
            "locality_id": locality_id,
            "acquisition_id": acquisition_id,
            "preparation_type_id": preparation_type_id,
        },
        db_path,
    )
    db.create_acquisition_document(
        {
            "acquisition_id": acquisition_id,
            "document_path": "FT-9000_receipt.pdf",
            "document_type_id": document_type_id,
            "title": "Receipt",
            "notes": "Document note.",
        },
        db_path,
    )
    db.create_specimen_image(
        {
            "specimen_id": specimen_id,
            "image_path": "FT-9000_overall.jpg",
            "image_type_id": image_type_id,
            "caption": "Overall view",
        },
        db_path,
    )
    db.create_observation(
        {
            "specimen_id": specimen_id,
            "observation_type": "General",
            "notes": "Observation note.",
        },
        db_path,
    )
    db.create_specimen_measurement(
        {
            "specimen_id": specimen_id,
            "measurement_type_id": measurement_type_id,
            "value": "42",
        },
        db_path,
    )
    db.create_related_link(
        {
            "specimen_id": specimen_id,
            "url": "https://example.test/specimen",
            "title": "Reference",
            "description": "Related link.",
        },
        db_path,
    )

    output_path = export_specimen_json(specimen_id, db_path)
    output_path.write_text("stale export")
    second_output_path = export_specimen_json(specimen_id, db_path)
    assert second_output_path == output_path
    payload = json.loads(output_path.read_text())

    assert output_path.parent == export_folder
    assert output_path.name == "FT-9000.json"
    assert payload["specimen"]["collection_code"] == "FT-9000"
    assert "id" not in payload["specimen"]
    assert "taxon_id" not in payload["specimen"]
    assert payload["specimen"]["taxonomy"] == "Dactylioceras commune"
    assert payload["specimen"]["geological_age"] == {
        "era": None,
        "period": "Jurassic",
        "epoch": "Early Jurassic",
        "stage": None,
        "min_ma": None,
        "max_ma": None,
    }
    assert payload["specimen"]["locality"] == {
        "locality_name": "Charmouth",
        "formation": None,
        "member": None,
        "region": "Dorset",
        "country": "England",
        "latitude": None,
        "longitude": None,
        "locality_precision": None,
        "locality_notes": None,
    }
    assert payload["specimen"]["preparation_type"] == "Prepared"
    assert payload["specimen"]["acquisition"] == "2026-07-03 - Example dealer"
    assert payload["taxonomy"]["genus"] == "Dactylioceras"
    assert "id" not in payload["taxonomy"]
    assert payload["provenance"]["source_name"] == "Example dealer"
    assert payload["documents"]["items"][0]["document_path"] == "FT-9000_receipt.pdf"
    assert "document_type_id" not in payload["documents"]["items"][0]
    assert payload["documents"]["items"][0]["document_type"] == "Acquisition Receipt"
    assert payload["images"]["items"][0]["image_path"] == "FT-9000_overall.jpg"
    assert "image_type_id" not in payload["images"]["items"][0]
    assert payload["images"]["items"][0]["image_type"] == "Overall"
    assert payload["notes"]["items"][0]["notes"] == "Observation note."
    assert "specimen_id" not in payload["notes"]["items"][0]
    assert "measurement_type_id" not in payload["measurements"]["items"][0]
    assert payload["measurements"]["items"][0]["measurement_type"] == "Length"
    assert payload["related links"]["items"][0]["url"] == "https://example.test/specimen"
    assert "specimen_id" not in payload["related links"]["items"][0]
