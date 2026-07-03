from yoyo import step

steps = [
    step(
        """
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
        """,
        "DROP TABLE IF EXISTS taxonomy;",
    ),
    step(
        """
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
        """,
        "DROP TABLE IF EXISTS localities;",
    ),
    step(
        """
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
        """,
        "DROP TABLE IF EXISTS geological_ages;",
    ),
    step(
        """
        CREATE TABLE preparation_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        "DROP TABLE IF EXISTS preparation_types;",
    ),
    step(
        "ALTER TABLE specimens ADD COLUMN taxon_id INTEGER REFERENCES taxonomy (id)",
        "ALTER TABLE specimens DROP COLUMN taxon_id",
    ),
    step(
        "ALTER TABLE specimens ADD COLUMN geological_age_id INTEGER REFERENCES geological_ages (id)",
        "ALTER TABLE specimens DROP COLUMN geological_age_id",
    ),
    step(
        "ALTER TABLE specimens ADD COLUMN locality_id INTEGER REFERENCES localities (id)",
        "ALTER TABLE specimens DROP COLUMN locality_id",
    ),
    step(
        "ALTER TABLE specimens ADD COLUMN preparation_type_id INTEGER REFERENCES preparation_types (id)",
        "ALTER TABLE specimens DROP COLUMN preparation_type_id",
    ),
    step(
        "CREATE INDEX idx_specimens_taxon_id ON specimens (taxon_id)",
        "DROP INDEX IF EXISTS idx_specimens_taxon_id",
    ),
    step(
        "CREATE INDEX idx_specimens_geological_age_id ON specimens (geological_age_id)",
        "DROP INDEX IF EXISTS idx_specimens_geological_age_id",
    ),
    step(
        "CREATE INDEX idx_specimens_locality_id ON specimens (locality_id)",
        "DROP INDEX IF EXISTS idx_specimens_locality_id",
    ),
    step(
        "CREATE INDEX idx_specimens_preparation_type_id ON specimens (preparation_type_id)",
        "DROP INDEX IF EXISTS idx_specimens_preparation_type_id",
    ),
    step(
        "CREATE INDEX idx_taxonomy_genus_species ON taxonomy (genus, species)",
        "DROP INDEX IF EXISTS idx_taxonomy_genus_species",
    ),
    step(
        "CREATE INDEX idx_localities_country_region ON localities (country, region)",
        "DROP INDEX IF EXISTS idx_localities_country_region",
    ),
    step(
        "CREATE INDEX idx_geological_ages_period ON geological_ages (period)",
        "DROP INDEX IF EXISTS idx_geological_ages_period",
    ),
    step(
        """
        INSERT INTO preparation_types (name, description, created_at, updated_at)
        VALUES
            ('Natural', 'Unprepared or naturally exposed specimen.', datetime('now'), datetime('now')),
            ('Polished', 'Polished specimen surface.', datetime('now'), datetime('now')),
            ('Split and polished', 'Split specimen with polished exposed surfaces.', datetime('now'), datetime('now')),
            ('Split', 'Split specimen without polishing.', datetime('now'), datetime('now')),
            ('Matrix', 'Specimen retained in matrix.', datetime('now'), datetime('now')),
            ('Prepared', 'Mechanically or chemically prepared specimen.', datetime('now'), datetime('now')),
            ('Cast', 'Cast or replica specimen.', datetime('now'), datetime('now'));
        """,
        "DELETE FROM preparation_types;",
    ),
    step(
        """
        INSERT INTO geological_ages (era, period, min_ma, max_ma, notes, created_at, updated_at)
        VALUES
            ('Palaeozoic', 'Cambrian', 485.4, 538.8, 'Seed period record.', datetime('now'), datetime('now')),
            ('Palaeozoic', 'Ordovician', 443.8, 485.4, 'Seed period record.', datetime('now'), datetime('now')),
            ('Palaeozoic', 'Silurian', 419.2, 443.8, 'Seed period record.', datetime('now'), datetime('now')),
            ('Palaeozoic', 'Devonian', 358.9, 419.2, 'Seed period record.', datetime('now'), datetime('now')),
            ('Palaeozoic', 'Carboniferous', 298.9, 358.9, 'Seed period record.', datetime('now'), datetime('now')),
            ('Palaeozoic', 'Permian', 251.9, 298.9, 'Seed period record.', datetime('now'), datetime('now')),
            ('Mesozoic', 'Triassic', 201.4, 251.9, 'Seed period record.', datetime('now'), datetime('now')),
            ('Mesozoic', 'Jurassic', 143.1, 201.4, 'Seed period record.', datetime('now'), datetime('now')),
            ('Mesozoic', 'Cretaceous', 66.0, 143.1, 'Seed period record.', datetime('now'), datetime('now')),
            ('Cenozoic', 'Paleogene', 23.03, 66.0, 'Seed period record.', datetime('now'), datetime('now')),
            ('Cenozoic', 'Neogene', 2.58, 23.03, 'Seed period record.', datetime('now'), datetime('now')),
            ('Cenozoic', 'Quaternary', 0.0, 2.58, 'Seed period record.', datetime('now'), datetime('now'));
        """,
        "DELETE FROM geological_ages WHERE notes = 'Seed period record.';",
    ),
    step(
        """
        INSERT INTO taxonomy (
            identification_notes,
            identification_confidence,
            created_at,
            updated_at
        )
        SELECT DISTINCT
            TRIM(taxonomic_identification),
            'Unknown',
            datetime('now'),
            datetime('now')
        FROM specimens
        WHERE taxonomic_identification IS NOT NULL
            AND TRIM(taxonomic_identification) != '';
        """,
        "DELETE FROM taxonomy WHERE genus IS NULL AND species IS NULL;",
    ),
    step(
        """
        UPDATE specimens
        SET taxon_id = (
            SELECT taxonomy.id
            FROM taxonomy
            WHERE taxonomy.identification_notes = TRIM(specimens.taxonomic_identification)
            ORDER BY taxonomy.id
            LIMIT 1
        )
        WHERE taxonomic_identification IS NOT NULL
            AND TRIM(taxonomic_identification) != '';
        """,
        "UPDATE specimens SET taxon_id = NULL;",
    ),
    step(
        """
        INSERT INTO localities (
            locality_name,
            country,
            created_at,
            updated_at
        )
        SELECT DISTINCT
            TRIM(formation_or_locality),
            NULLIF(TRIM(country_region), ''),
            datetime('now'),
            datetime('now')
        FROM specimens
        WHERE formation_or_locality IS NOT NULL
            AND TRIM(formation_or_locality) != '';
        """,
        "DELETE FROM localities WHERE formation IS NULL AND member IS NULL;",
    ),
    step(
        """
        UPDATE specimens
        SET locality_id = (
            SELECT localities.id
            FROM localities
            WHERE localities.locality_name = TRIM(specimens.formation_or_locality)
            ORDER BY localities.id
            LIMIT 1
        )
        WHERE formation_or_locality IS NOT NULL
            AND TRIM(formation_or_locality) != '';
        """,
        "UPDATE specimens SET locality_id = NULL;",
    ),
    step(
        """
        UPDATE specimens
        SET geological_age_id = (
            SELECT geological_ages.id
            FROM geological_ages
            WHERE LOWER(specimens.geological_age) LIKE '%' || LOWER(geological_ages.period) || '%'
            ORDER BY geological_ages.min_ma DESC
            LIMIT 1
        )
        WHERE geological_age IS NOT NULL
            AND TRIM(geological_age) != '';
        """,
        "UPDATE specimens SET geological_age_id = NULL;",
    ),
    step(
        """
        UPDATE specimens
        SET preparation_type_id = (
            SELECT preparation_types.id
            FROM preparation_types
            WHERE LOWER(preparation_types.name) = LOWER(TRIM(specimens.preparation_type))
            LIMIT 1
        )
        WHERE preparation_type IS NOT NULL
            AND TRIM(preparation_type) != '';
        """,
        "UPDATE specimens SET preparation_type_id = NULL;",
    ),
]
