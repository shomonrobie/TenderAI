# fix_missing_columns.py
import sqlite3

def add_missing_columns():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    columns_to_add = [
        ("expected_profit", "REAL"),
        ("expected_value", "REAL"),
        ("slt_threshold", "REAL"),
        ("nppi_factor", "REAL"),
        ("weighted_average", "REAL"),
        ("final_submitted_bid", "REAL"),
        ("is_final_submitted", "INTEGER DEFAULT 0"),
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE tender_analyses ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"⚠ Column already exists: {col_name}")
            else:
                print(f"Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == "__main__":
    add_missing_columns()