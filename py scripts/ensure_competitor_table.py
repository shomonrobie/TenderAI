# ensure_competitor_table.py
import sqlite3
from datetime import datetime

def ensure_competitor_table():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Create competitor master table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS competitor_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        competitor_name TEXT,
        business_type TEXT,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        notes TEXT,
        first_seen DATE,
        last_seen DATE,
        total_bids INTEGER DEFAULT 0,
        total_wins INTEGER DEFAULT 0,
        avg_bid_ratio REAL,
        preferred_strategy TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id),
        UNIQUE(company_id, competitor_name)
    )
    ''')
    
    # Add competitor_id to historical_tenders if not exists
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN competitor_id INTEGER")
        print("✓ Added competitor_id column")
    except sqlite3.OperationalError:
        print("⚠ competitor_id column already exists")
    
    # Create index
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_competitor_master ON competitor_master(company_id, competitor_name)')
    
    conn.commit()
    conn.close()
    print("✅ Competitor master table verified/created")

if __name__ == "__main__":
    ensure_competitor_table()