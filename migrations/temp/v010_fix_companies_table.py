version = "v010_fix_companies_table"

# migrations/v010_fix_companies_table.py - NEW FILE

import sqlite3
import os

def upgrade(db_path="data/tender_system.db"):
    """Add missing columns to companies table"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 Running migration v010: Fix Companies Table")
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add missing columns
    columns_to_add = {
        'district': 'TEXT',
        'upazila': 'TEXT',
        'post_code': 'TEXT',
        'is_individual': 'BOOLEAN DEFAULT 0',
        'status': "TEXT DEFAULT 'active'",
        'registration_number': 'TEXT',
        'vat_number': 'TEXT',
        'website': 'TEXT'
    }
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE companies ADD COLUMN {col_name} {col_type}")
                print(f"  ✅ Added column: {col_name}")
            except Exception as e:
                print(f"  ⚠️ Could not add {col_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration v010 completed successfully!")

if __name__ == "__main__":
    upgrade()