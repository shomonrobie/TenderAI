# update_competitor_master.py
import sqlite3

def add_competitor_master_tables():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Create competitor master table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS competitor_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        competitor_name TEXT UNIQUE,
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
        FOREIGN KEY (company_id) REFERENCES companies (id)
    )
    ''')
    
    # Add competitor_id to historical_tenders
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN competitor_id INTEGER")
        print("✓ Added competitor_id column to historical_tenders")
    except sqlite3.OperationalError:
        print("⚠ competitor_id column already exists")
    
    # Add total_bidders to historical_tenders
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN total_bidders INTEGER")
        print("✓ Added total_bidders column to historical_tenders")
    except sqlite3.OperationalError:
        print("⚠ total_bidders column already exists")
     # Add total_bidders to historical_tenders
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN our_rank INTEGER")
        print("✓ Added our_rank column to historical_tenders")
    except sqlite3.OperationalError:
        print("⚠ our_rank column already exists")

    # Create index
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_competitor_master ON competitor_master(company_id, competitor_name)')
    
    conn.commit()
    conn.close()
    print("Competitor master tables added successfully!")

if __name__ == "__main__":
    add_competitor_master_tables()