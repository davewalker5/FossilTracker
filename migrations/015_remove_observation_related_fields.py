from yoyo import step

steps = [
    step(
        "ALTER TABLE observations DROP COLUMN related_project",
        "ALTER TABLE observations ADD COLUMN related_project TEXT",
    ),
    step(
        "ALTER TABLE observations DROP COLUMN related_url",
        "ALTER TABLE observations ADD COLUMN related_url TEXT",
    ),
]
