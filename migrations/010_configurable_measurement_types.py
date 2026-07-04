from yoyo import step

steps = [
    step(
        """
        CREATE TABLE measurement_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            unit TEXT NOT NULL,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        "DROP TABLE IF EXISTS measurement_types;",
    ),
    step(
        "CREATE INDEX idx_measurement_types_active ON measurement_types (active)",
        "DROP INDEX IF EXISTS idx_measurement_types_active;",
    ),
    step(
        """
        INSERT INTO measurement_types (name, unit, active, created_at, updated_at)
        VALUES
            ('Length', 'mm', 1, datetime('now'), datetime('now')),
            ('Width', 'mm', 1, datetime('now'), datetime('now')),
            ('Height', 'mm', 1, datetime('now'), datetime('now')),
            ('Diameter', 'mm', 1, datetime('now'), datetime('now')),
            ('Weight', 'g', 1, datetime('now'), datetime('now')),
            ('Thickness', 'mm', 1, datetime('now'), datetime('now')),
            ('Aperture Width', 'mm', 1, datetime('now'), datetime('now')),
            ('Aperture Height', 'mm', 1, datetime('now'), datetime('now')),
            ('Bore Diameter', 'mm', 1, datetime('now'), datetime('now')),
            ('Maximum Preserved Length', 'mm', 1, datetime('now'), datetime('now')),
            ('Matrix Length', 'mm', 1, datetime('now'), datetime('now')),
            ('Matrix Width', 'mm', 1, datetime('now'), datetime('now')),
            ('Matrix Height', 'mm', 1, datetime('now'), datetime('now'));
        """,
        "DELETE FROM measurement_types;",
    ),
]
