from yoyo import step

steps = [
    step(
        """
        INSERT OR IGNORE INTO document_types (name, description, created_at, updated_at)
        VALUES
            ('Acquisition Receipt', 'Proof of purchase or invoice', datetime('now'), datetime('now')),
            ('Appraisal / Valuation', 'Insurance valuation or appraisal documents', datetime('now'), datetime('now')),
            ('Book Extract', 'Relevant pages from a book', datetime('now'), datetime('now')),
            ('Certificate of Authenticity', 'Certificate supplied by a dealer or institution', datetime('now'), datetime('now')),
            ('Collection Label', 'Original label accompanying the specimen', datetime('now'), datetime('now')),
            ('Correspondence', 'Emails or letters relating to the specimen', datetime('now'), datetime('now')),
            ('Dealer Information', 'Seller''s catalogue page, description, or stock sheet', datetime('now'), datetime('now')),
            ('Exhibition Record', 'Documents relating to display or loan', datetime('now'), datetime('now')),
            ('Export / Permit', 'Collection permits, export/import paperwork where applicable', datetime('now'), datetime('now')),
            ('Field Notes', 'Scanned field notebook pages or field records', datetime('now'), datetime('now')),
            ('Geological Reference', 'Stratigraphic information, formation descriptions, geological notes.', datetime('now'), datetime('now')),
            ('Identification Notes', 'Working identification, expert opinions, comparison notes', datetime('now'), datetime('now')),
            ('Locality Information', 'Site descriptions, maps, locality notes, GPS documentation', datetime('now'), datetime('now')),
            ('Other', NULL, datetime('now'), datetime('now')),
            ('Preparation Record', 'Notes or reports describing preparation or conservation work', datetime('now'), datetime('now')),
            ('Provenance Document', 'Ownership history or provenance statement', datetime('now'), datetime('now')),
            ('Scientific Paper', 'Published paper relevant to the specimen or locality', datetime('now'), datetime('now'));
        """,
        "SELECT 1;",
    ),
    step(
        """
        UPDATE document_types
        SET
            description = CASE name
                WHEN 'Acquisition Receipt' THEN 'Proof of purchase or invoice'
                WHEN 'Appraisal / Valuation' THEN 'Insurance valuation or appraisal documents'
                WHEN 'Book Extract' THEN 'Relevant pages from a book'
                WHEN 'Certificate of Authenticity' THEN 'Certificate supplied by a dealer or institution'
                WHEN 'Collection Label' THEN 'Original label accompanying the specimen'
                WHEN 'Correspondence' THEN 'Emails or letters relating to the specimen'
                WHEN 'Dealer Information' THEN 'Seller''s catalogue page, description, or stock sheet'
                WHEN 'Exhibition Record' THEN 'Documents relating to display or loan'
                WHEN 'Export / Permit' THEN 'Collection permits, export/import paperwork where applicable'
                WHEN 'Field Notes' THEN 'Scanned field notebook pages or field records'
                WHEN 'Geological Reference' THEN 'Stratigraphic information, formation descriptions, geological notes.'
                WHEN 'Identification Notes' THEN 'Working identification, expert opinions, comparison notes'
                WHEN 'Locality Information' THEN 'Site descriptions, maps, locality notes, GPS documentation'
                WHEN 'Other' THEN NULL
                WHEN 'Preparation Record' THEN 'Notes or reports describing preparation or conservation work'
                WHEN 'Provenance Document' THEN 'Ownership history or provenance statement'
                WHEN 'Scientific Paper' THEN 'Published paper relevant to the specimen or locality'
                ELSE description
            END,
            updated_at = datetime('now')
        WHERE name IN (
            'Acquisition Receipt',
            'Appraisal / Valuation',
            'Book Extract',
            'Certificate of Authenticity',
            'Collection Label',
            'Correspondence',
            'Dealer Information',
            'Exhibition Record',
            'Export / Permit',
            'Field Notes',
            'Geological Reference',
            'Identification Notes',
            'Locality Information',
            'Other',
            'Preparation Record',
            'Provenance Document',
            'Scientific Paper'
        );
        """,
        """
        UPDATE document_types
        SET description = NULL,
            updated_at = datetime('now')
        WHERE name IN (
            'Acquisition Receipt',
            'Appraisal / Valuation',
            'Book Extract',
            'Certificate of Authenticity',
            'Collection Label',
            'Correspondence',
            'Dealer Information',
            'Exhibition Record',
            'Export / Permit',
            'Field Notes',
            'Geological Reference',
            'Identification Notes',
            'Locality Information',
            'Other',
            'Preparation Record',
            'Provenance Document',
            'Scientific Paper'
        );
        """,
    ),
]
