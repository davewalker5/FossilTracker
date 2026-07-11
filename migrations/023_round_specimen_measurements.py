from yoyo import step


steps = [
    step(
        """
        UPDATE specimen_measurements
        SET value = CAST(ROUND(CAST(value AS REAL), 3) AS TEXT)
        WHERE value IS NOT NULL;
        """,
        "SELECT 1;",
    ),
]
