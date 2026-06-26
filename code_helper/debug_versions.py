# fix_unique_constraint.py

from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()

print("=== Fixing UNIQUE constraint on rate_versions ===")

try:
    # Step 1: Create a new table with the correct schema
    cursor.execute("""
        CREATE TABLE rate_versions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            version_name TEXT NOT NULL,
            edition_year INTEGER NOT NULL,
            version_number INTEGER DEFAULT 1,
            effective_from DATE,
            effective_to DATE,
            is_active BOOLEAN DEFAULT 0,
            released_by TEXT,
            release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            total_parents INTEGER DEFAULT 0,
            total_children INTEGER DEFAULT 0,
            total_rates INTEGER DEFAULT 0,
            created_by TEXT,
            has_sections BOOLEAN DEFAULT FALSE,
            chapter_numbers TEXT,
            section_numbers TEXT,
            updated_at TIMESTAMP,
            UNIQUE(source, edition_year, version_number)
        )
    """)
    print("✅ Created rate_versions_new table with correct UNIQUE constraint")

    # Step 2: Copy data from old table to new table
    cursor.execute("""
        INSERT INTO rate_versions_new (
            id, source, version_name, edition_year, version_number,
            effective_from, effective_to, is_active, released_by,
            release_date, notes, total_parents, total_children,
            total_rates, created_by, has_sections, chapter_numbers,
            section_numbers, updated_at
        )
        SELECT 
            id, source, version_name, edition_year, 
            COALESCE(version_number, 1) as version_number,
            effective_from, effective_to, is_active, released_by,
            release_date, notes, total_parents, total_children,
            total_rates, created_by, 
            COALESCE(has_sections, 0) as has_sections,
            chapter_numbers, section_numbers, updated_at
        FROM rate_versions
    """)
    print(f"✅ Copied {cursor.rowcount} records to new table")

    # Step 3: Drop old table
    cursor.execute("DROP TABLE rate_versions")
    print("✅ Dropped old rate_versions table")

    # Step 4: Rename new table to original name
    cursor.execute("ALTER TABLE rate_versions_new RENAME TO rate_versions")
    print("✅ Renamed new table to rate_versions")

    # Step 5: Recreate indexes
    cursor.execute("CREATE INDEX idx_version_source ON rate_versions(source)")
    cursor.execute("CREATE INDEX idx_version_active ON rate_versions(is_active)")
    cursor.execute("CREATE INDEX idx_version_edition ON rate_versions(edition_year)")
    print("✅ Recreated indexes")

    conn.commit()
    print("\n✅ Migration completed successfully!")
    print("✅ New UNIQUE constraint: (source, edition_year, version_number)")

except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()

# Verify the new constraint
print("\n=== Verification ===")
conn2 = db.get_connection()
cursor2 = conn2.cursor()

cursor2.execute("PRAGMA index_list('rate_versions')")
indexes = cursor2.fetchall()
print("Indexes on rate_versions:")
for idx in indexes:
    print(f"  - {idx}")

# Try to insert duplicate to test
try:
    cursor2.execute("""
        INSERT INTO rate_versions (source, edition_year, version_number, version_name)
        VALUES ('TEST', 2025, 1, 'Test Version')
    """)
    print("\n✅ Test insert with (TEST, 2025, 1) succeeded")
    
    # Try duplicate with same source, edition_year but different version_number
    cursor2.execute("""
        INSERT INTO rate_versions (source, edition_year, version_number, version_name)
        VALUES ('TEST', 2025, 2, 'Test Version 2')
    """)
    print("✅ Test insert with (TEST, 2025, 2) succeeded (different version_number)")
    
    conn2.commit()
except Exception as e:
    print(f"Expected: Cannot insert duplicate (TEST, 2025, 1): {e}")

conn2.close()