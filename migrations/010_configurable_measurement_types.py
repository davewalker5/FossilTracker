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
            ('Matrix Height', 'mm', 1, datetime('now'), datetime('now')),
            ('Shell Diameter (D)', 'mm', 1, datetime('now'), datetime('now')),
            ('Umbilical Diameter (U)', 'mm', 1, datetime('now'), datetime('now')),
            ('Whorl Height (Wh)', 'mm', 1, datetime('now'), datetime('now')),
            ('Whorl Width (Ww)', 'mm', 1, datetime('now'), datetime('now')),
            ('Umbilical Ratio (U/D)', 'None', 1, datetime('now'), datetime('now')),
            ('Relative Whorl Height (Wh/D)', 'None', 1, datetime('now'), datetime('now')),
            ('Relative Shell Thickness (Ww/D)', 'None', 1, datetime('now'), datetime('now')),
            ('Whorl Shape (Ww/Wh)', 'None', 1, datetime('now'), datetime('now')),
            ('Number of Visible Whorls', 'None', 1, datetime('now'), datetime('now')),
            ('Rib Density', 'None', 1, datetime('now'), datetime('now')),
            ('Shell Length (L)', 'mm', 1, datetime('now'), datetime('now')),
            ('Maximum Diameter', 'mm', 1, datetime('now'), datetime('now')),
            ('Minimum Diameter', 'mm', 1, datetime('now'), datetime('now')),
            ('Number of Visible Chambers', 'None', 1, datetime('now'), datetime('now')),
            ('Average Chamber Spacing', 'mm', 1, datetime('now'), datetime('now')),
            ('Siphuncle Position', 'None', 1, datetime('now'), datetime('now')),
            ('Siphuncle Diameter', 'mm', 1, datetime('now'), datetime('now')),
            ('Expansion Angle', 'degrees', 1, datetime('now'), datetime('now')),
            ('Taper Rate', 'mm/mm', 1, datetime('now'), datetime('now')),
            ('Chambers per cm', 'chambers/cm', 1, datetime('now'), datetime('now'));
        """,
        "DELETE FROM measurement_types;",
    ),
]
