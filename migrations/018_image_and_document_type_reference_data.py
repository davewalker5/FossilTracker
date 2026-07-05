from yoyo import step

steps = [
    step(
        """
        CREATE TABLE image_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        "DROP TABLE IF EXISTS image_types;",
    ),
    step(
        """
        CREATE TABLE document_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        "DROP TABLE IF EXISTS document_types;",
    ),
    step(
        """
        INSERT INTO image_types (name, created_at, updated_at)
        VALUES
            ('Overall', datetime('now'), datetime('now')),
            ('Close-up', datetime('now'), datetime('now')),
            ('Matrix', datetime('now'), datetime('now')),
            ('Label', datetime('now'), datetime('now')),
            ('Comparison', datetime('now'), datetime('now')),
            ('Other', datetime('now'), datetime('now'));
        """,
        "DELETE FROM image_types;",
    ),
    step(
        """
        INSERT OR IGNORE INTO image_types (name, created_at, updated_at)
        SELECT DISTINCT TRIM(image_type), datetime('now'), datetime('now')
        FROM specimen_images
        WHERE image_type IS NOT NULL
            AND TRIM(image_type) != '';
        """,
        """
        DELETE FROM image_types
        WHERE name NOT IN ('Overall', 'Close-up', 'Matrix', 'Label', 'Comparison', 'Other');
        """,
    ),
    step(
        """
        INSERT INTO document_types (name, created_at, updated_at)
        VALUES
            ('Acquisition Receipt', datetime('now'), datetime('now')),
            ('Certificate of Authenticity', datetime('now'), datetime('now')),
            ('Provenance Document', datetime('now'), datetime('now')),
            ('Collection Label', datetime('now'), datetime('now')),
            ('Dealer Information', datetime('now'), datetime('now')),
            ('Locality Information', datetime('now'), datetime('now')),
            ('Geological Reference', datetime('now'), datetime('now')),
            ('Identification Notes', datetime('now'), datetime('now')),
            ('Scientific Paper', datetime('now'), datetime('now')),
            ('Book Extract', datetime('now'), datetime('now')),
            ('Preparation Record', datetime('now'), datetime('now')),
            ('Export / Permit', datetime('now'), datetime('now')),
            ('Appraisal / Valuation', datetime('now'), datetime('now')),
            ('Exhibition Record', datetime('now'), datetime('now')),
            ('Correspondence', datetime('now'), datetime('now')),
            ('Field Notes', datetime('now'), datetime('now')),
            ('Other', datetime('now'), datetime('now'));
        """,
        "DELETE FROM document_types;",
    ),
    step(
        """
        INSERT OR IGNORE INTO document_types (name, created_at, updated_at)
        SELECT DISTINCT TRIM(document_type), datetime('now'), datetime('now')
        FROM acquisition_documents
        WHERE document_type IS NOT NULL
            AND TRIM(document_type) != '';
        """,
        """
        DELETE FROM document_types
        WHERE name NOT IN (
            'Acquisition Receipt',
            'Certificate of Authenticity',
            'Provenance Document',
            'Collection Label',
            'Dealer Information',
            'Locality Information',
            'Geological Reference',
            'Identification Notes',
            'Scientific Paper',
            'Book Extract',
            'Preparation Record',
            'Export / Permit',
            'Appraisal / Valuation',
            'Exhibition Record',
            'Correspondence',
            'Field Notes',
            'Other'
        );
        """,
    ),
    step(
        "ALTER TABLE specimen_images ADD COLUMN image_type_id INTEGER REFERENCES image_types (id)",
        "ALTER TABLE specimen_images DROP COLUMN image_type_id",
    ),
    step(
        """
        UPDATE specimen_images
        SET image_type_id = (
            SELECT image_types.id
            FROM image_types
            WHERE LOWER(image_types.name) = LOWER(TRIM(specimen_images.image_type))
            LIMIT 1
        )
        WHERE image_type IS NOT NULL
            AND TRIM(image_type) != '';
        """,
        """
        UPDATE specimen_images
        SET image_type = (
            SELECT image_types.name
            FROM image_types
            WHERE image_types.id = specimen_images.image_type_id
        )
        WHERE image_type_id IS NOT NULL;
        """,
    ),
    step(
        "ALTER TABLE specimen_images DROP COLUMN image_type",
        "ALTER TABLE specimen_images ADD COLUMN image_type TEXT",
    ),
    step(
        """
        ALTER TABLE acquisition_documents
        ADD COLUMN document_type_id INTEGER REFERENCES document_types (id)
        """,
        "ALTER TABLE acquisition_documents DROP COLUMN document_type_id",
    ),
    step(
        """
        UPDATE acquisition_documents
        SET document_type_id = (
            SELECT document_types.id
            FROM document_types
            WHERE LOWER(document_types.name) = LOWER(TRIM(acquisition_documents.document_type))
            LIMIT 1
        )
        WHERE document_type IS NOT NULL
            AND TRIM(document_type) != '';
        """,
        """
        UPDATE acquisition_documents
        SET document_type = (
            SELECT document_types.name
            FROM document_types
            WHERE document_types.id = acquisition_documents.document_type_id
        )
        WHERE document_type_id IS NOT NULL;
        """,
    ),
    step(
        "ALTER TABLE acquisition_documents DROP COLUMN document_type",
        "ALTER TABLE acquisition_documents ADD COLUMN document_type TEXT",
    ),
]
