# debug_sections.py
import sys
import pandas as pd
from database.db_manager import DatabaseManager

# Initialize database
db = UnifiedDatabaseManager()

# Run the query
conn = db.get_connection()
result = pd.read_sql_query("""
    SELECT s.section_number, s.section_name, c.chapter_number
    FROM rate_sections s
    JOIN rate_chapters c ON s.chapter_id = c.id
    WHERE c.source = 'LGED'
""", conn)

print("\n=== Sections in Database ===")
print(result)

# Also check chapters
chapters = pd.read_sql_query("""
    SELECT id, chapter_number, version_id 
    FROM rate_chapters 
    WHERE source = 'LGED'
""", conn)

print("\n=== Chapters in Database ===")
print(chapters)

conn.close()
