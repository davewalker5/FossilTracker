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
    image_paths TEXT,
    field_notes_links TEXT,
    public_notes TEXT,
    private_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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


if __name__ == "__main__":
    unittest.main()
