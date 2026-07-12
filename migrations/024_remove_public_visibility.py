from yoyo import step


steps = [
    step(
        "ALTER TABLE specimens DROP COLUMN public_visible",
        "ALTER TABLE specimens ADD COLUMN public_visible INTEGER NOT NULL DEFAULT 1",
    ),
    step(
        "ALTER TABLE observations DROP COLUMN public_visible",
        "ALTER TABLE observations ADD COLUMN public_visible INTEGER NOT NULL DEFAULT 1",
    ),
]
