from yoyo import step

steps = [
    step(
        """
        CREATE TEMP TABLE taxonomy_migration_state AS
        SELECT COALESCE(MAX(id), 0) AS max_taxonomy_id
        FROM taxonomy
        """,
        "DROP TABLE IF EXISTS taxonomy_migration_state",
    ),
    step(
        """
        CREATE TEMP TABLE taxonomy_specimen_duplicates AS
        SELECT
            specimens.id AS specimen_id,
            specimens.taxon_id AS original_taxon_id,
            ROW_NUMBER() OVER (
                PARTITION BY specimens.taxon_id
                ORDER BY specimens.id
            ) AS link_number
        FROM specimens
        WHERE specimens.taxon_id IS NOT NULL
        """,
        "DROP TABLE IF EXISTS taxonomy_specimen_duplicates",
    ),
    step(
        """
        INSERT INTO taxonomy (
            kingdom,
            phylum,
            class_name,
            order_name,
            family,
            genus,
            species,
            identification_confidence,
            identification_notes,
            created_at,
            updated_at
        )
        SELECT
            taxonomy.kingdom,
            taxonomy.phylum,
            taxonomy.class_name,
            taxonomy.order_name,
            taxonomy.family,
            taxonomy.genus,
            taxonomy.species,
            taxonomy.identification_confidence,
            taxonomy.identification_notes,
            datetime('now'),
            datetime('now')
        FROM taxonomy_specimen_duplicates
        JOIN taxonomy ON taxonomy.id = taxonomy_specimen_duplicates.original_taxon_id
        WHERE taxonomy_specimen_duplicates.link_number > 1
        ORDER BY taxonomy_specimen_duplicates.specimen_id
        """,
        """
        DELETE FROM taxonomy
        WHERE id NOT IN (
            SELECT taxon_id
            FROM specimens
            WHERE taxon_id IS NOT NULL
        )
        """,
    ),
    step(
        """
        CREATE TEMP TABLE taxonomy_specimen_replacements AS
        WITH duplicate_specimens AS (
            SELECT
                specimen_id,
                ROW_NUMBER() OVER (ORDER BY specimen_id) AS copy_number
            FROM taxonomy_specimen_duplicates
            WHERE link_number > 1
        ),
        copied_taxonomy AS (
            SELECT
                id AS new_taxon_id,
                ROW_NUMBER() OVER (ORDER BY id) AS copy_number
            FROM taxonomy
            WHERE id > (
                SELECT max_taxonomy_id
                FROM taxonomy_migration_state
            )
        )
        SELECT
            duplicate_specimens.specimen_id,
            copied_taxonomy.new_taxon_id
        FROM duplicate_specimens
        JOIN copied_taxonomy
            ON copied_taxonomy.copy_number = duplicate_specimens.copy_number
        """,
        "DROP TABLE IF EXISTS taxonomy_specimen_replacements",
    ),
    step(
        """
        UPDATE specimens
        SET taxon_id = (
            SELECT taxonomy_specimen_replacements.new_taxon_id
            FROM taxonomy_specimen_replacements
            WHERE taxonomy_specimen_replacements.specimen_id = specimens.id
        )
        WHERE specimens.id IN (
            SELECT specimen_id
            FROM taxonomy_specimen_replacements
        )
        """,
        "UPDATE specimens SET taxon_id = taxon_id",
    ),
    step(
        "DROP TABLE taxonomy_specimen_replacements",
        "CREATE TEMP TABLE taxonomy_specimen_replacements (specimen_id INTEGER, new_taxon_id INTEGER)",
    ),
    step(
        "DROP TABLE taxonomy_specimen_duplicates",
        "CREATE TEMP TABLE taxonomy_specimen_duplicates (specimen_id INTEGER, original_taxon_id INTEGER, link_number INTEGER)",
    ),
    step(
        "DROP TABLE taxonomy_migration_state",
        "CREATE TEMP TABLE taxonomy_migration_state (max_taxonomy_id INTEGER)",
    ),
    step(
        """
        CREATE UNIQUE INDEX idx_specimens_taxon_id_unique
        ON specimens (taxon_id)
        WHERE taxon_id IS NOT NULL
        """,
        "DROP INDEX IF EXISTS idx_specimens_taxon_id_unique",
    ),
]
