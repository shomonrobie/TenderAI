# update_winner_column.py
import sqlite3

def add_winner_column():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN winning_company_type TEXT")
        print("✓ Added winning_company_type column")
    except sqlite3.OperationalError:
        print("⚠ winning_company_type column already exists")
    
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN our_awarded_price REAL")
        print("✓ Added our_awarded_price column")
    except sqlite3.OperationalError:
        print("⚠ our_awarded_price column already exists")
    
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    add_winner_column()