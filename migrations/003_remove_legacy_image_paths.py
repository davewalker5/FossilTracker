from yoyo import step

steps = [
    step(
        "ALTER TABLE specimens DROP COLUMN image_paths",
        "ALTER TABLE specimens ADD COLUMN image_paths TEXT",
    )
]
