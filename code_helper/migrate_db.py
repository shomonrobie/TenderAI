# migrate_db.py
import sqlite3

def migrate_database():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Check and add columns to historical_tenders
    columns_to_check = [
        ("winning_company_type", "TEXT"),
        ("our_awarded_price", "REAL"),
        ("winning_competitor", "TEXT")
    ]
    
    for col_name, col_type in columns_to_check:
        try:
            cursor.execute(f"ALTER TABLE historical_tenders ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"⚠ Column {col_name} already exists")
            else:
                print(f"Error: {e}")
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_winner_type ON historical_tenders(winning_company_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_award_date ON historical_tenders(award_date)")
    
    conn.commit()
    conn.close()
    print("Database migration complete!")

if __name__ == "__main__":
    migrate_database()