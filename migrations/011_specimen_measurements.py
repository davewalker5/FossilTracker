from yoyo import step

steps = [
    step(
        """
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
        """,
        "DROP TABLE IF EXISTS specimen_measurements;",
    ),
    step(
        "CREATE INDEX idx_specimen_measurements_specimen_id ON specimen_measurements (specimen_id)",
        "DROP INDEX IF EXISTS idx_specimen_measurements_specimen_id;",
    ),
    step(
        "CREATE INDEX idx_specimen_measurements_measurement_type_id ON specimen_measurements (measurement_type_id)",
        "DROP INDEX IF EXISTS idx_specimen_measurements_measurement_type_id;",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN measurements",
        "ALTER TABLE specimens ADD COLUMN measurements TEXT",
    ),
]
