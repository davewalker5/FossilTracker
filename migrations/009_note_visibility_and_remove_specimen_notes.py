from yoyo import step

steps = [
    step(
        "ALTER TABLE observations ADD COLUMN public_visible INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE observations DROP COLUMN public_visible",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN public_notes",
        "ALTER TABLE specimens ADD COLUMN public_notes TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN private_notes",
        "ALTER TABLE specimens ADD COLUMN private_notes TEXT",
    ),
]
