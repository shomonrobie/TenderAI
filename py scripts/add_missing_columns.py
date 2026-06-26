# add_missing_columns.py
import sqlite3

def add_missing_columns():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(tender_analyses)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # Columns to add if missing
    columns_to_add = {
        'analysis_type': 'TEXT DEFAULT "Basic"',
        'analysis_date': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
        'bid_status': 'TEXT DEFAULT "Pending"',
        'actual_bid': 'REAL'
    }
    
    print("Checking and adding missing columns...")
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE tender_analyses ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"⚠ Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    print("\n✅ Database update completed!")

if __name__ == "__main__":
    add_missing_columns()