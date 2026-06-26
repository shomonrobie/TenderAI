# migrations/v011_add_company_columns.py

import sqlite3
import os

version = "v011_add_company_columns"

def upgrade(db_path="data/tender_system.db"):
    """Add missing columns to companies table"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 Running migration v011: Adding company columns for e-GP")
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(companies)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # Define columns to add
    columns_to_add = {
        'tin_number': 'TEXT',
        'bin_number': 'TEXT',
        'rjsc_number': 'TEXT',
        'upazila': 'TEXT',
        'post_code': 'TEXT',
        'status': "TEXT DEFAULT 'active'",
        'updated_at': 'TIMESTAMP'
    }
    
    # Add missing columns
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE companies ADD COLUMN {col_name} {col_type}")
                print(f"  ✅ Added column: {col_name}")
            except Exception as e:
                print(f"  ⚠️ Could not add {col_name}: {e}")
    
    # Create additional tables if not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            license_type TEXT NOT NULL,
            license_number TEXT NOT NULL,
            issuing_authority TEXT,
            issue_date DATE,
            expiry_date DATE,
            license_file_path TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ Created company_licenses table")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            fiscal_year TEXT NOT NULL,
            annual_turnover REAL,
            construction_turnover REAL,
            net_worth REAL,
            working_capital REAL,
            liquid_assets REAL,
            credit_limit REAL,
            bank_guarantee_limit REAL,
            is_audited BOOLEAN DEFAULT 0,
            audit_firm TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ Created company_financials table")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            designation TEXT NOT NULL,
            nid_number TEXT,
            phone TEXT,
            email TEXT,
            educational_qualification TEXT,
            experience_years INTEGER,
            is_key_personnel BOOLEAN DEFAULT 0,
            cv_file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ Created company_personnel table")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT,
            description TEXT,
            document_date DATE,
            expiry_date DATE,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER
        )
    """)
    print("  ✅ Created company_documents table")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration v011 completed successfully!")

def downgrade(db_path="data/tender_system.db"):
    """Rollback migration (drop added columns - SQLite doesn't support dropping columns easily)"""
    print("⚠️ Downgrade not available for column additions")
    pass

if __name__ == "__main__":
    upgrade()