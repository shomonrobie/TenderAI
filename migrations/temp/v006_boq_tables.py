# migrations/v006_boq_tables.py (updated)

version = "v006"

def up(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("  Creating/Updating BOQ tables...")
    
    # BOQ generation history with all columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boq_generation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_id INTEGER,
            tender_id TEXT,
            tender_title TEXT,
            procuring_entity TEXT,
            file_name TEXT,
            item_count INTEGER DEFAULT 0,
            total_estimated_cost REAL DEFAULT 0,
            selected_zone TEXT,
            rate_source TEXT,
            edition_year INTEGER,
            status TEXT DEFAULT 'draft',
            notes TEXT,
            is_locked BOOLEAN DEFAULT 0,
            locked_at TIMESTAMP,
            locked_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)
    
    # Add missing columns if table already existed
    cursor.execute("PRAGMA table_info(boq_generation_history)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    columns_to_add = {
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
        'updated_at': 'TIMESTAMP',
        'is_locked': 'BOOLEAN DEFAULT 0',
        'locked_at': 'TIMESTAMP',
        'locked_by': 'INTEGER'
    }
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE boq_generation_history ADD COLUMN {col_name} {col_type}")
                print(f"    Added column: {col_name}")
            except Exception as e:
                print(f"    Could not add {col_name}: {e}")
    
    # BOQ items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boq_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boq_id INTEGER NOT NULL,
            item_code TEXT NOT NULL,
            description TEXT,
            unit TEXT,
            quantity REAL DEFAULT 0,
            unit_rate REAL DEFAULT 0,
            total REAL DEFAULT 0,
            is_custom BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (boq_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE
        )
    """)
    
    # BOQ approval history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boq_approval_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boq_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            comment TEXT,
            user_id INTEGER,
            username TEXT,
            user_role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (boq_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE
        )
    """)
    
    # BOQ activity log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boq_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boq_id INTEGER,
            action TEXT,
            details TEXT,
            user_id INTEGER,
            username TEXT,
            user_role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (boq_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE
        )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_company ON boq_generation_history(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_status ON boq_generation_history(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_items_boq ON boq_items(boq_id)")
    
    conn.commit()
    conn.close()
    print("  ✅ BOQ tables created/updated successfully")