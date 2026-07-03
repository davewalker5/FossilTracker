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
    taxonomic_identification TEXT,
    geological_age TEXT,
    formation_or_locality TEXT,
    country_region TEXT,
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
    preparation_type TEXT,
    storage_location TEXT,
    field_notes_links TEXT,
    public_notes TEXT,
    private_notes TEXT,
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
        specimen_id = db.create_specimen(
            {
                "collection_code": "FT-1000",
                "title": "Test ammonite",
                "taxonomic_identification": "Ammonoidea",
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


if __name__ == "__main__":
    unittest.main()
