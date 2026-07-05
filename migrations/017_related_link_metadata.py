from yoyo import step

steps = [
    step(
        "ALTER TABLE specimen_related_links ADD COLUMN title TEXT",
        "ALTER TABLE specimen_related_links DROP COLUMN title",
    ),
    step(
        "ALTER TABLE specimen_related_links ADD COLUMN description TEXT",
        "ALTER TABLE specimen_related_links DROP COLUMN description",
    ),
]
