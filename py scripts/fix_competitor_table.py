# fix_competitor_table.py
import sqlite3

def fix_table():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Check if competitor_master exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='competitor_master'")
    if not cursor.fetchone():
        print("Creating competitor_master table...")
        cursor.execute('''
        CREATE TABLE competitor_master (
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
            avg_bid_ratio REAL DEFAULT 0.90,
            preferred_strategy TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Table created successfully!")
    else:
        print("competitor_master table already exists")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_table()
    print("Done!")