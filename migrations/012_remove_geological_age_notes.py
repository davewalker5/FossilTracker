from yoyo import step

steps = [
    step(
        "ALTER TABLE geological_ages DROP COLUMN notes",
        "ALTER TABLE geological_ages ADD COLUMN notes TEXT",
    ),
]
