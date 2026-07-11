from yoyo import step


steps = [
    step(
        """
        INSERT OR IGNORE INTO measurement_types (name, unit, description, created_at, updated_at)
        VALUES
            ('Shell Diameter (D)', 'mm', NULL, datetime('now'), datetime('now')),
            ('Umbilical Diameter (U)', 'mm', NULL, datetime('now'), datetime('now')),
            ('Whorl Height (Wh)', 'mm', NULL, datetime('now'), datetime('now')),
            ('Whorl Width (Ww)', 'mm', NULL, datetime('now'), datetime('now')),
            ('Umbilical Ratio (U/D)', 'None', NULL, datetime('now'), datetime('now')),
            ('Relative Whorl Height (Wh/D)', 'None', NULL, datetime('now'), datetime('now')),
            ('Relative Shell Thickness (Ww/D)', 'None', NULL, datetime('now'), datetime('now')),
            ('Whorl Shape (Ww/Wh)', 'None', NULL, datetime('now'), datetime('now')),
            ('Number of Visible Whorls', 'None', NULL, datetime('now'), datetime('now')),
            ('Rib Density', 'None', NULL, datetime('now'), datetime('now'));
        """,
        "SELECT 1;",
    ),
]
