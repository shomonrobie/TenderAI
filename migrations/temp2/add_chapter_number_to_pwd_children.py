# migrations/add_chapter_number_to_pwd_children.py
import sqlite3
import sys
from pathlib import Path

def run_migration():
    db_path = Path("data/tender_system.db")  # ← Change if your DB path is different
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("🔍 Checking current schema...")

        # Check if column already exists
        cursor.execute("PRAGMA table_info(pwd_children)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'chapter_number' in columns:
            print("✅ Column 'chapter_number' already exists in pwd_children table.")
            return

        print("⚡ Adding column 'chapter_number' to pwd_children...")

        # Add the new column
        cursor.execute("""
            ALTER TABLE pwd_children 
            ADD COLUMN chapter_number TEXT
        """)

        # Optional: Backfill chapter_number for existing records
        print("🔄 Backfilling chapter_number from parents...")
        cursor.execute("""
            UPDATE pwd_children 
            SET chapter_number = (
                SELECT chapter_number 
                FROM pwd_parents 
                WHERE pwd_parents.pwd_code = pwd_children.parent_code
            )
            WHERE chapter_number IS NULL 
              AND parent_code IN (SELECT pwd_code FROM pwd_parents)
        """)

        conn.commit()

        # Verify
        cursor.execute("PRAGMA table_info(pwd_children)")
        new_columns = [row[1] for row in cursor.fetchall()]
        
        print("✅ Migration completed successfully!")
        print(f"Current columns in pwd_children: {new_columns}")
        
        # Show sample data
        cursor.execute("""
            SELECT pwd_code, parent_code, chapter_number 
            FROM pwd_children 
            LIMIT 5
        """)
        print("\nSample data:")
        for row in cursor.fetchall():
            print(row)

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()