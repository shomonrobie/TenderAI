# migrations/v008_extension_tables.py

import sqlite3

version = "v008_extension_tables"

def upgrade(db_path="data/tender_system.db"):
    """Add extension auto-fill tracking tables"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("  🔧 Creating extension_auto_fill_log table...")
    
    # Create extension auto-fill log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extension_auto_fill_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            field_label TEXT,
            confidence_score REAL,
            page_url TEXT,
            filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_extension_log_company 
        ON extension_auto_fill_log(company_id, filled_at)
    """)
    
    # Add extension_auto_fills column to subscription_plans if exists
    cursor.execute("PRAGMA table_info(subscription_plans)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'extension_auto_fills' not in columns:
        try:
            cursor.execute("""
                ALTER TABLE subscription_plans 
                ADD COLUMN extension_auto_fills INTEGER DEFAULT 5
            """)
            
            # Update existing plans
            cursor.execute("""
                UPDATE subscription_plans 
                SET extension_auto_fills = CASE plan_name
                    WHEN 'free' THEN 5
                    WHEN 'basic' THEN 30
                    WHEN 'professional' THEN 100
                    WHEN 'enterprise' THEN -1
                    ELSE 5
                END
            """)
            print("  ✅ Added extension_auto_fills column to subscription_plans")
        except Exception as e:
            print(f"  ⚠️ Could not add column: {e}")
    
    conn.commit()
    conn.close()
    print("  ✅ extension_auto_fill_log table created")

if __name__ == "__main__":
    upgrade()