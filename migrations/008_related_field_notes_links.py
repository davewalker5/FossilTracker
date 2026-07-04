from yoyo import step

steps = [
    step(
        """
        CREATE TABLE specimen_related_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specimen_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
        );
        """,
        "DROP TABLE IF EXISTS specimen_related_links;",
    ),
    step(
        """
        CREATE INDEX idx_specimen_related_links_specimen_id
        ON specimen_related_links (specimen_id);
        """,
        "DROP INDEX IF EXISTS idx_specimen_related_links_specimen_id;",
    ),
    step(
        """
        INSERT INTO specimen_related_links (
            specimen_id,
            url,
            created_at,
            updated_at
        )
        WITH RECURSIVE split_links(specimen_id, url, remaining, updated_at) AS (
            SELECT
                id,
                '',
                REPLACE(field_notes_links, char(13), '') || char(10),
                updated_at
            FROM specimens
            WHERE field_notes_links IS NOT NULL
                AND TRIM(field_notes_links) != ''
            UNION ALL
            SELECT
                specimen_id,
                TRIM(SUBSTR(remaining, 1, INSTR(remaining, char(10)) - 1)),
                SUBSTR(remaining, INSTR(remaining, char(10)) + 1),
                updated_at
            FROM split_links
            WHERE remaining != ''
        )
        SELECT
            specimen_id,
            url,
            updated_at,
            updated_at
        FROM split_links
        WHERE url != '';
        """,
        """
        DELETE FROM specimen_related_links;
        """,
    ),
    step(
        "ALTER TABLE specimens DROP COLUMN field_notes_links",
        "ALTER TABLE specimens ADD COLUMN field_notes_links TEXT",
    ),
]
