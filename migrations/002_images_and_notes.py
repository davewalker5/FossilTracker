from yoyo import step

steps = [
    step(
        """
        CREATE TABLE specimen_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specimen_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            image_type TEXT,
            caption TEXT,
            photographer TEXT,
            licence TEXT,
            date_taken TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
        );
        """,
        "DROP TABLE IF EXISTS specimen_images;",
    ),
    step(
        """
        CREATE TABLE observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specimen_id INTEGER NOT NULL,
            observation_date TEXT,
            observation_type TEXT,
            notes TEXT NOT NULL,
            related_project TEXT,
            related_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (specimen_id) REFERENCES specimens (id) ON DELETE CASCADE
        );
        """,
        "DROP TABLE IF EXISTS observations;",
    ),
    step(
        "CREATE INDEX idx_specimen_images_specimen_id ON specimen_images (specimen_id)",
        "DROP INDEX IF EXISTS idx_specimen_images_specimen_id",
    ),
    step(
        "CREATE INDEX idx_observations_specimen_id ON observations (specimen_id)",
        "DROP INDEX IF EXISTS idx_observations_specimen_id",
    ),
    step(
        "CREATE INDEX idx_observations_observation_date ON observations (observation_date)",
        "DROP INDEX IF EXISTS idx_observations_observation_date",
    ),
    step(
        """
        INSERT INTO specimen_images (
            specimen_id,
            image_path,
            image_type,
            caption,
            created_at,
            updated_at
        )
        SELECT
            id,
            image_paths,
            'Legacy path',
            'Imported from the original specimen image path field',
            updated_at,
            updated_at
        FROM specimens
        WHERE image_paths IS NOT NULL
            AND TRIM(image_paths) != '';
        """,
        """
        DELETE FROM specimen_images
        WHERE image_type = 'Legacy path'
            AND caption = 'Imported from the original specimen image path field';
        """,
    ),
]
