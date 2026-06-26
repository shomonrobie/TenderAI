# migrations/add_chapter_number_to_pwd_children.py
import sqlite3
import sys
from pathlib import Path
from database.unified_db_manager import UnifiedDatabaseManager

DEBUG_MODE = True

db = UnifiedDatabaseManager()

# =============================================================================
# DATABASE MIGRATION: Add missing columns
# =============================================================================

def run_migration2():
    """Add missing columns to existing tables"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if is_active exists in tender_milestones
        cursor.execute("PRAGMA table_info(tender_milestones)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_active' not in columns:
            print("🔧 Adding is_active column to tender_milestones...")
            cursor.execute("""
                ALTER TABLE tender_milestones 
                ADD COLUMN is_active INTEGER DEFAULT 1
            """)
            conn.commit()
            print("✅ Added is_active column to tender_milestones")
        
        # Check if other missing columns exist
        if 'completed_at' not in columns:
            print("🔧 Adding completed_at column to tender_milestones...")
            cursor.execute("""
                ALTER TABLE tender_milestones 
                ADD COLUMN completed_at TIMESTAMP
            """)
            conn.commit()
            print("✅ Added completed_at column to tender_milestones")
        
        # Check tender_team_assignments table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tender_team_assignments'")
        if not cursor.fetchone():
            print("🔧 Creating tender_team_assignments table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tender_team_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tender_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (tender_id) REFERENCES company_tenders(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
            print("✅ Created tender_team_assignments table")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

# Run migration on module load
run_migration2()