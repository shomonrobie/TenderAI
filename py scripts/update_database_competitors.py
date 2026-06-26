# update_database_competitors.py
import sqlite3

def add_competitor_columns():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Add competitor-related columns to historical_tenders
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN competitors_data TEXT")
        print("✓ Added competitors_data column")
    except sqlite3.OperationalError:
        print("⚠ competitors_data column already exists")
    
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN winning_competitor TEXT")
        print("✓ Added winning_competitor column")
    except sqlite3.OperationalError:
        print("⚠ winning_competitor column already exists")
    
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN our_rank INTEGER")
        print("✓ Added our_rank column")
    except sqlite3.OperationalError:
        print("⚠ our_rank column already exists")
    
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN total_bidders INTEGER")
        print("✓ Added total_bidders column")
    except sqlite3.OperationalError:
        print("⚠ total_bidders column already exists")
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN competitors_data TEXT")
        print("✓ Added competitors_data column")
    except sqlite3.OperationalError:
        print("⚠ competitors_data column already exists")
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN winning_competitor TEXT")
        print("✓ Added winning_competitor column")
    except sqlite3.OperationalError:
        print("⚠ winning_competitor column already exists")    
    try:
        cursor.execute("ALTER TABLE historical_tenders ADD COLUMN notes TEXT")
        print("✓ Added notes column")
    except sqlite3.OperationalError:
        print("⚠ notes column already exists")        
    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == "__main__":
    add_competitor_columns()