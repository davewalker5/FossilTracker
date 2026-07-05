from yoyo import step

steps = [
    step(
        "ALTER TABLE taxonomy ADD COLUMN subclass TEXT",
        "ALTER TABLE taxonomy DROP COLUMN subclass",
    ),
]
