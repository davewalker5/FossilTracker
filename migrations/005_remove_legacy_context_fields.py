from yoyo import step

steps = [
    step(
        "DROP INDEX IF EXISTS idx_specimens_taxonomic_identification",
        "CREATE INDEX idx_specimens_taxonomic_identification ON specimens (taxonomic_identification)",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN taxonomic_identification",
        "ALTER TABLE specimens ADD COLUMN taxonomic_identification TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN geological_age",
        "ALTER TABLE specimens ADD COLUMN geological_age TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN formation_or_locality",
        "ALTER TABLE specimens ADD COLUMN formation_or_locality TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN country_region",
        "ALTER TABLE specimens ADD COLUMN country_region TEXT",
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN preparation_type",
        "ALTER TABLE specimens ADD COLUMN preparation_type TEXT",
    ),
]
