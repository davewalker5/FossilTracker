from yoyo import step

steps = [
    step(
        "DROP INDEX IF EXISTS idx_measurement_types_active",
        "CREATE INDEX idx_measurement_types_active ON measurement_types (active)",
    ),
    step(
        "ALTER TABLE measurement_types DROP COLUMN active",
        "ALTER TABLE measurement_types ADD COLUMN active INTEGER NOT NULL DEFAULT 1",
    ),
]
