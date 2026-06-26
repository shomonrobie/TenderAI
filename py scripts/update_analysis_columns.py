# update_analysis_columns.py
import sqlite3

def update_columns():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Add is_final_submitted column if not exists
    try:
        cursor.execute("ALTER TABLE tender_analyses ADD COLUMN is_final_submitted INTEGER DEFAULT 0")
        print("✓ Added is_final_submitted column")
    except:
        print("⚠ is_final_submitted already exists")
    
    # Add final_submitted_bid column if not exists
    try:
        cursor.execute("ALTER TABLE tender_analyses ADD COLUMN final_submitted_bid REAL")
        print("✓ Added final_submitted_bid column")
    except:
        print("⚠ final_submitted_bid already exists")
    
    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == "__main__":
    update_columns()