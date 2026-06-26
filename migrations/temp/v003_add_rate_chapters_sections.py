# v003_add_rate_chapters_sections.py

version = "v003"

def up(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("  Creating rate_chapters table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source VARCHAR(20) NOT NULL,
            version_id INTEGER,
            chapter_number VARCHAR(20) NOT NULL,
            chapter_name TEXT,
            description TEXT,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES rate_versions(id) ON DELETE CASCADE,
            UNIQUE(source, chapter_number, version_id)
        )
    """)
    
    print("  Creating rate_sections table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source VARCHAR(20) NOT NULL,
            version_id INTEGER,
            chapter_id INTEGER NOT NULL,
            section_number VARCHAR(20) NOT NULL,
            section_name TEXT,
            description TEXT,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES rate_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES rate_chapters(id) ON DELETE CASCADE,
            UNIQUE(source, chapter_id, section_number, version_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("  ✅ Rate chapters and sections tables created")