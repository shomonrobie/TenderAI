# add_columns.py - Add all missing columns

import sqlite3

DB_PATH = "data/tender_system.db"

def add_all_missing_columns():
    """Add all missing columns to tenant rate tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔧 ADDING MISSING COLUMNS")
    print("=" * 60)
    
    # ========== tenant_rate_items ==========
    cursor.execute("PRAGMA table_info(tenant_rate_items)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print("\n📋 tenant_rate_items - Adding missing columns:")
    
    if 'base_rate_reference' not in columns:
        cursor.execute("ALTER TABLE tenant_rate_items ADD COLUMN base_rate_reference REAL DEFAULT 0.0")
        print("  ✅ Added base_rate_reference")
    
    if 'cost_factor' not in columns:
        cursor.execute("ALTER TABLE tenant_rate_items ADD COLUMN cost_factor REAL DEFAULT 0.0")
        print("  ✅ Added cost_factor")
    
    # ========== boq_generation_history ==========
    cursor.execute("PRAGMA table_info(boq_generation_history)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print("\n📋 boq_generation_history - Adding missing columns:")
    
    if 'rate_book_id' not in columns:
        cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN rate_book_id INTEGER")
        print("  ✅ Added rate_book_id")
    
    if 'version_id' not in columns:
        cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN version_id INTEGER")
        print("  ✅ Added version_id")
    
    if 'aggressive_total' not in columns:
        cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN aggressive_total REAL DEFAULT 0.0")
        print("  ✅ Added aggressive_total")
    
    if 'competitive_total' not in columns:
        cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN competitive_total REAL DEFAULT 0.0")
        print("  ✅ Added competitive_total")
    
    if 'standard_total' not in columns:
        cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN standard_total REAL DEFAULT 0.0")
        print("  ✅ Added standard_total")
    
    if 'selected_scenario' not in columns:
        cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN selected_scenario TEXT")
        print("  ✅ Added selected_scenario")
    
    conn.commit()
    conn.close()
    
    print("\n✅ All columns added successfully!")


def create_missing_tables():
    """Create missing tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n📋 Creating missing tables:")
    
    # company_cost_profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_cost_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            profile_name TEXT DEFAULT 'Default',
            aggressive_factor REAL DEFAULT 0.78,
            competitive_factor REAL DEFAULT 0.82,
            standard_factor REAL DEFAULT 0.86,
            markup_percentage REAL DEFAULT 15.0,
            overhead_percentage REAL DEFAULT 10.0,
            profit_margin_percentage REAL DEFAULT 15.0,
            is_active BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)
    print("  ✅ Created company_cost_profiles")
    
    # cost_level_definitions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cost_level_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level_code TEXT UNIQUE NOT NULL,
            level_name TEXT NOT NULL,
            description TEXT,
            default_factor REAL,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ Created cost_level_definitions")
    
    # Insert default cost levels
    cursor.execute("""
        INSERT OR IGNORE INTO cost_level_definitions (level_code, level_name, description, default_factor, display_order)
        VALUES 
            ('AGGRESSIVE', 'Aggressive Cost', 'Minimum cost, lean operations, reduced overhead', 0.78, 1),
            ('COMPETITIVE', 'Competitive Cost', 'Balanced cost, normal operations, standard overhead', 0.82, 2),
            ('STANDARD', 'Standard Cost', 'Premium cost, full overhead, conservative approach', 0.86, 3)
    """)
    print("  ✅ Inserted default cost levels")
    
    # cost_scenario_results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cost_scenario_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT,
            company_id INTEGER,
            scenario_name TEXT NOT NULL,
            total_cost REAL NOT NULL,
            recommended_bid REAL NOT NULL,
            profit REAL NOT NULL,
            profit_margin REAL NOT NULL,
            win_probability REAL,
            risk_level TEXT,
            competitor_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            is_selected BOOLEAN DEFAULT 0,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    print("  ✅ Created cost_scenario_results")
    
    conn.commit()
    conn.close()
    
    print("\n✅ All tables created successfully!")


if __name__ == "__main__":
    add_all_missing_columns()
    create_missing_tables()
    print("\n" + "=" * 60)
    print("✅ COLUMNS AND TABLES READY!")
    print("=" * 60)