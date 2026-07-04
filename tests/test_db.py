from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fossil_tracker import db


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
    notes TEXT,
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

CREATE TABLE measurement_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    unit TEXT NOT NULL,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
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
    document_type TEXT,
    title TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (acquisition_id) REFERENCES acquisitions (id) ON DELETE CASCADE
);

CREATE TABLE specimen_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    image_type TEXT,
    caption TEXT,
    photographer TEXT,
    licence TEXT,
    date_taken TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
);

CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    observation_date TEXT,
    observation_type TEXT,
    notes TEXT NOT NULL,
    related_project TEXT,
    related_url TEXT,
    public_visible INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
);

CREATE TABLE specimen_related_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specimen_id INTEGER NOT NULL,
    url TEXT NOT NULL,
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
"""


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(SCHEMA)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_filter_specimen(self) -> None:
        taxon_id = db.create_taxonomy(
            {
                "identification_notes": "Ammonoidea",
                "identification_confidence": "High",
            },
            self.db_path,
        )
        specimen_id = db.create_specimen(
            {
                "collection_code": "FT-1000",
                "title": "Test ammonite",
                "taxon_id": taxon_id,
            },
            self.db_path,
        )

        specimen = db.get_specimen(specimen_id, self.db_path)
        self.assertIsNotNone(specimen)
        self.assertEqual(specimen["collection_code"], "FT-1000")

        filtered = db.list_specimens(self.db_path, search="ammonite")
        self.assertEqual(len(filtered), 1)

    def test_seed_only_when_empty(self) -> None:
        self.assertEqual(db.seed_specimens(self.db_path), 1)
        self.assertEqual(db.seed_specimens(self.db_path), 0)
        self.assertEqual(db.specimen_count(self.db_path), 1)

    def test_create_image_and_observation_records(self) -> None:
        specimen_id = db.create_specimen(
            {
                "collection_code": "FT-2000",
                "title": "Image and notes test",
            },
            self.db_path,
        )

        image_id = db.create_specimen_image(
            {
                "specimen_id": specimen_id,
                "image_path": "data/images/FT-2000.jpg",
                "image_type": "Overall",
                "caption": "Overall view",
                "photographer": "D. Walker",
                "licence": "Private",
                "date_taken": "2026-07-03",
                "notes": "Shows the complete specimen.",
            },
            self.db_path,
        )
        observation_id = db.create_observation(
            {
                "specimen_id": specimen_id,
                "observation_date": "2026-07-03",
                "observation_type": "Morphology",
                "notes": "**Markdown** observation note.",
                "related_project": "Shell morphology",
                "related_url": "https://example.com/project",
                "public_visible": True,
            },
            self.db_path,
        )

        images = db.list_specimen_images(specimen_id, self.db_path)
        observations = db.list_observations(specimen_id, self.db_path)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["id"], image_id)
        self.assertEqual(images[0]["caption"], "Overall view")
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["id"], observation_id)
        self.assertEqual(observations[0]["notes"], "**Markdown** observation note.")
        self.assertEqual(observations[0]["public_visible"], 1)

        db.delete_specimen_image(image_id, self.db_path)
        db.delete_observation(observation_id, self.db_path)
        self.assertEqual(db.list_specimen_images(specimen_id, self.db_path), [])
        self.assertEqual(db.list_observations(specimen_id, self.db_path), [])

    def test_create_related_links_and_cascade_delete(self) -> None:
        specimen_id = db.create_specimen(
            {
                "collection_code": "FT-2500",
                "title": "Related links test",
            },
            self.db_path,
        )
        first_link_id = db.create_related_link(
            {
                "specimen_id": specimen_id,
                "url": "https://fieldnotes.example/first",
            },
            self.db_path,
        )
        db.create_related_link(
            {
                "specimen_id": specimen_id,
                "url": "https://fieldnotes.example/second",
            },
            self.db_path,
        )

        links = db.list_related_links(specimen_id, self.db_path)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[1]["id"], first_link_id)
        self.assertEqual(links[1]["url"], "https://fieldnotes.example/first")

        db.delete_related_link(first_link_id, self.db_path)
        links = db.list_related_links(specimen_id, self.db_path)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["url"], "https://fieldnotes.example/second")

        db.delete_specimen(specimen_id, self.db_path)
        self.assertEqual(db.list_related_links(specimen_id, self.db_path), [])

    def test_create_context_records_and_link_specimen(self) -> None:
        taxon_id = db.create_taxonomy(
            {
                "kingdom": "Animalia",
                "phylum": "Mollusca",
                "class_name": "Cephalopoda",
                "genus": "Dactylioceras",
                "species": "commune",
                "identification_confidence": "Medium",
            },
            self.db_path,
        )
        age_id = db.create_geological_age(
            {
                "era": "Mesozoic",
                "period": "Jurassic",
                "epoch": "Early Jurassic",
                "max_ma": "201.4",
                "min_ma": "174.7",
            },
            self.db_path,
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
            self.db_path,
        )
        preparation_type_id = db.create_preparation_type(
            {"name": "Prepared", "description": "Prepared specimen."},
            self.db_path,
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
            self.db_path,
        )

        specimen = db.get_specimen(specimen_id, self.db_path)
        self.assertEqual(specimen["taxon_id"], taxon_id)
        self.assertEqual(specimen["geological_age_id"], age_id)
        self.assertEqual(specimen["locality_id"], locality_id)
        self.assertEqual(specimen["preparation_type_id"], preparation_type_id)
        self.assertEqual(db.get_taxonomy(taxon_id, self.db_path)["genus"], "Dactylioceras")
        self.assertEqual(db.get_geological_age(age_id, self.db_path)["period"], "Jurassic")
        self.assertEqual(db.get_locality(locality_id, self.db_path)["country"], "England")

    def test_create_update_and_delete_measurement_type(self) -> None:
        measurement_type_id = db.create_measurement_type(
            {
                "name": "Umbilicus Diameter",
                "unit": "mm",
                "description": "Ammonite umbilicus diameter.",
            },
            self.db_path,
        )

        measurement_type = db.get_measurement_type(measurement_type_id, self.db_path)
        self.assertEqual(measurement_type["name"], "Umbilicus Diameter")
        self.assertEqual(measurement_type["unit"], "mm")
        self.assertEqual(measurement_type["active"], 1)

        db.update_measurement_type(
            measurement_type_id,
            {
                "name": "Umbilicus Width",
                "unit": "mm",
                "description": "Updated description.",
                "active": False,
            },
            self.db_path,
        )
        updated = db.get_measurement_type(measurement_type_id, self.db_path)
        self.assertEqual(updated["name"], "Umbilicus Width")
        self.assertEqual(updated["description"], "Updated description.")
        self.assertEqual(updated["active"], 0)

        measurement_types = db.list_measurement_types(self.db_path)
        self.assertEqual([row["id"] for row in measurement_types], [measurement_type_id])

        db.delete_measurement_type(measurement_type_id, self.db_path)
        self.assertEqual(db.list_measurement_types(self.db_path), [])

    def test_measurement_type_name_is_unique_case_insensitive(self) -> None:
        db.create_measurement_type({"name": "Length", "unit": "mm"}, self.db_path)
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_measurement_type({"name": "length", "unit": "mm"}, self.db_path)

    def test_create_specimen_measurements_and_cascade_delete(self) -> None:
        specimen_id = db.create_specimen(
            {
                "collection_code": "FT-3500",
                "title": "Measured specimen",
            },
            self.db_path,
        )
        measurement_type_id = db.create_measurement_type(
            {
                "name": "Length",
                "unit": "mm",
            },
            self.db_path,
        )
        measurement_id = db.create_specimen_measurement(
            {
                "specimen_id": specimen_id,
                "measurement_type_id": measurement_type_id,
                "value": "43.2",
            },
            self.db_path,
        )

        measurements = db.list_specimen_measurements(specimen_id, self.db_path)
        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0]["id"], measurement_id)
        self.assertEqual(measurements[0]["measurement_name"], "Length")
        self.assertEqual(measurements[0]["measurement_unit"], "mm")
        self.assertEqual(measurements[0]["value"], "43.2")

        with self.assertRaises(sqlite3.IntegrityError):
            db.create_specimen_measurement(
                {
                    "specimen_id": specimen_id,
                    "measurement_type_id": measurement_type_id,
                    "value": "44.0",
                },
                self.db_path,
            )

        db.delete_specimen_measurement(measurement_id, self.db_path)
        self.assertEqual(db.list_specimen_measurements(specimen_id, self.db_path), [])

        measurement_id = db.create_specimen_measurement(
            {
                "specimen_id": specimen_id,
                "measurement_type_id": measurement_type_id,
                "value": "43.2",
            },
            self.db_path,
        )
        self.assertIsInstance(measurement_id, int)
        db.delete_specimen(specimen_id, self.db_path)
        self.assertEqual(db.list_specimen_measurements(specimen_id, self.db_path), [])

    def test_create_acquisition_and_document_records(self) -> None:
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
            self.db_path,
        )
        document_id = db.create_acquisition_document(
            {
                "acquisition_id": acquisition_id,
                "document_path": "data/documents/receipt.pdf",
                "document_type": "Receipt",
                "title": "Purchase receipt",
            },
            self.db_path,
        )
        specimen_id = db.create_specimen(
            {
                "collection_code": "FT-4000",
                "title": "Provenance specimen",
                "acquisition_id": acquisition_id,
                "public_visible": True,
            },
            self.db_path,
        )

        acquisition = db.get_acquisition(acquisition_id, self.db_path)
        specimen = db.get_specimen(specimen_id, self.db_path)
        documents = db.list_acquisition_documents(acquisition_id, self.db_path)
        self.assertEqual(acquisition["source_name"], "Example dealer")
        self.assertTrue(db.has_acquisition_documents(acquisition_id, self.db_path))
        self.assertEqual(specimen["acquisition_id"], acquisition_id)
        self.assertEqual(specimen["public_visible"], 1)
        self.assertEqual(documents[0]["id"], document_id)
        filtered = db.list_specimens(self.db_path, documented_only=True)
        self.assertEqual([row["id"] for row in filtered], [specimen_id])

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
            self.db_path,
        )
        updated = db.get_acquisition(acquisition_id, self.db_path)
        self.assertEqual(updated["source_name"], "Updated dealer")
        self.assertEqual(updated["source_type"], "Auction")
        self.assertEqual(updated["ethical_confidence"], "Medium")


if __name__ == "__main__":
    unittest.main()
