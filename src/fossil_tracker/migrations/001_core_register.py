from yoyo import step

steps = [
    step(
        """
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
        """,
        """
        DROP TABLE IF EXISTS specimens;
        """,
    ),
    step(
        "CREATE INDEX idx_specimens_collection_code ON specimens (collection_code)",
        "DROP INDEX IF EXISTS idx_specimens_collection_code",
    ),
    step(
        "CREATE INDEX idx_specimens_taxonomic_identification ON specimens (taxonomic_identification)",
        "DROP INDEX IF EXISTS idx_specimens_taxonomic_identification",
    ),
    step(
        "CREATE INDEX idx_specimens_ethical_confidence ON specimens (ethical_confidence)",
        "DROP INDEX IF EXISTS idx_specimens_ethical_confidence",
    ),
]
