from yoyo import step

steps = [
    step(
        "ALTER TABLE acquisitions DROP COLUMN documentation_available",
        "ALTER TABLE acquisitions ADD COLUMN documentation_available INTEGER NOT NULL DEFAULT 0",
    ),
    step(
        "ALTER TABLE acquisitions DROP COLUMN receipt_file",
        "ALTER TABLE acquisitions ADD COLUMN receipt_file TEXT",
    ),
]
