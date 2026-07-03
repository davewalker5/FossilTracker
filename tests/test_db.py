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
    acquisition_date TEXT,
    source TEXT,
    purchase_price TEXT,
    currency TEXT,
    provenance_notes TEXT,
    legality_ethics_notes TEXT,
    ethical_confidence TEXT NOT NULL DEFAULT 'Unknown',
    documentation_available INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    measurements TEXT,
    preparation_type_id INTEGER,
    storage_location TEXT,
    field_notes_links TEXT,
    public_notes TEXT,
    private_notes TEXT,
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
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
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
                "ethical_confidence": "High",
                "documentation_available": True,
            },
            self.db_path,
        )

        specimen = db.get_specimen(specimen_id, self.db_path)
        self.assertIsNotNone(specimen)
        self.assertEqual(specimen["collection_code"], "FT-1000")
        self.assertEqual(specimen["documentation_available"], 1)

        filtered = db.list_specimens(self.db_path, search="ammonite", confidence="High", documented_only=True)
        self.assertEqual(len(filtered), 1)

    def test_seed_only_when_empty(self) -> None:
        self.assertEqual(db.seed_specimens(self.db_path), 3)
        self.assertEqual(db.seed_specimens(self.db_path), 0)
        self.assertEqual(db.specimen_count(self.db_path), 3)

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

        db.delete_specimen_image(image_id, self.db_path)
        db.delete_observation(observation_id, self.db_path)
        self.assertEqual(db.list_specimen_images(specimen_id, self.db_path), [])
        self.assertEqual(db.list_observations(specimen_id, self.db_path), [])

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


if __name__ == "__main__":
    unittest.main()
