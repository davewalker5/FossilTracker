from yoyo import step


steps = [
    step(
        """
        INSERT OR IGNORE INTO measurement_types (name, unit, description, created_at, updated_at)
        VALUES
            ('Shell Length (L)', 'mm', 'Maximum preserved shell length', datetime('now'), datetime('now')),
            ('Maximum Diameter', 'mm', 'Largest external shell diameter', datetime('now'), datetime('now')),
            ('Minimum Diameter', 'mm', 'Diameter at the narrowest preserved end', datetime('now'), datetime('now')),
            ('Number of Visible Chambers', 'None', 'Number of preserved septal chambers visible', datetime('now'), datetime('now')),
            ('Average Chamber Spacing', 'mm', 'Average distance between adjacent septa', datetime('now'), datetime('now')),
            ('Siphuncle Position', 'None', 'Position of the siphuncle within the shell', datetime('now'), datetime('now')),
            ('Siphuncle Diameter', 'mm', 'External diameter of the siphuncle where visible', datetime('now'), datetime('now')),
            ('Expansion Angle', 'degrees', 'Calculated angle of shell expansion', datetime('now'), datetime('now')),
            ('Taper Rate', 'mm/mm', 'Diameter increase per millimetre of shell length', datetime('now'), datetime('now')),
            ('Chambers per cm', 'chambers/cm', 'Visible chambers per centimetre of shell length', datetime('now'), datetime('now'));
        """,
        "SELECT 1;",
    ),
]
