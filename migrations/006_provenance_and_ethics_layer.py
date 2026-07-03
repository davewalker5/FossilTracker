from yoyo import step

steps = [
    step(
        """
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
            documentation_available INTEGER NOT NULL DEFAULT 0,
            receipt_file TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        "DROP TABLE IF EXISTS acquisitions;",
    ),
    step(
        """
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
        """,
        "DROP TABLE IF EXISTS acquisition_documents;",
    ),
    step(
        "ALTER TABLE specimens ADD COLUMN acquisition_id INTEGER REFERENCES acquisitions (id)",
        "ALTER TABLE specimens DROP COLUMN acquisition_id",
    ),
    step(
        "ALTER TABLE specimens ADD COLUMN public_visible INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE specimens DROP COLUMN public_visible",
    ),
    step(
        "CREATE INDEX idx_specimens_acquisition_id ON specimens (acquisition_id)",
        "DROP INDEX IF EXISTS idx_specimens_acquisition_id",
    ),
    step(
        "CREATE INDEX idx_acquisitions_ethical_confidence ON acquisitions (ethical_confidence)",
        "DROP INDEX IF EXISTS idx_acquisitions_ethical_confidence",
    ),
    step(
        "CREATE INDEX idx_acquisition_documents_acquisition_id ON acquisition_documents (acquisition_id)",
        "DROP INDEX IF EXISTS idx_acquisition_documents_acquisition_id",
    ),
    step(
        """
        INSERT INTO acquisitions (
            acquisition_date,
            source_name,
            purchase_price,
            currency,
            provenance_summary,
            legality_notes,
            ethical_confidence,
            documentation_available,
            created_at,
            updated_at
        )
        SELECT
            acquisition_date,
            source,
            purchase_price,
            currency,
            provenance_notes,
            legality_ethics_notes,
            COALESCE(NULLIF(ethical_confidence, ''), 'Unknown'),
            documentation_available,
            created_at,
            updated_at
        FROM specimens
        WHERE acquisition_date IS NOT NULL
            OR source IS NOT NULL
            OR purchase_price IS NOT NULL
            OR currency IS NOT NULL
            OR provenance_notes IS NOT NULL
            OR legality_ethics_notes IS NOT NULL
            OR ethical_confidence IS NOT NULL
            OR documentation_available != 0;
        """,
        "DELETE FROM acquisitions;",
    ),
    step(
        """
        UPDATE specimens
        SET acquisition_id = (
            SELECT acquisitions.id
            FROM acquisitions
            WHERE COALESCE(acquisitions.acquisition_date, '') = COALESCE(specimens.acquisition_date, '')
                AND COALESCE(acquisitions.source_name, '') = COALESCE(specimens.source, '')
                AND COALESCE(acquisitions.provenance_summary, '') = COALESCE(specimens.provenance_notes, '')
                AND COALESCE(acquisitions.legality_notes, '') = COALESCE(specimens.legality_ethics_notes, '')
            ORDER BY acquisitions.id
            LIMIT 1
        );
        """,
        "UPDATE specimens SET acquisition_id = NULL;",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN acquisition_date",
        "ALTER TABLE specimens ADD COLUMN acquisition_date TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN source",
        "ALTER TABLE specimens ADD COLUMN source TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN purchase_price",
        "ALTER TABLE specimens ADD COLUMN purchase_price TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN currency",
        "ALTER TABLE specimens ADD COLUMN currency TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN provenance_notes",
        "ALTER TABLE specimens ADD COLUMN provenance_notes TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN legality_ethics_notes",
        "ALTER TABLE specimens ADD COLUMN legality_ethics_notes TEXT",
    ),
    step(
        "DROP INDEX IF EXISTS idx_specimens_ethical_confidence",
        "CREATE INDEX idx_specimens_ethical_confidence ON specimens (ethical_confidence)",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN ethical_confidence",
        "ALTER TABLE specimens ADD COLUMN ethical_confidence TEXT NOT NULL DEFAULT 'Unknown'",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN documentation_available",
        "ALTER TABLE specimens ADD COLUMN documentation_available INTEGER NOT NULL DEFAULT 0",
    ),
]
