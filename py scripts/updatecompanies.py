import sqlite3

def update_columns():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # List of columns to add with their types
    columns_to_add = [
        "is_locked BOOLEAN DEFAULT 0",
        "locked_at TIMESTAMP",
        "locked_by INTEGER",
        "is_copy BOOLEAN DEFAULT 0",
        "original_tender_id INTEGER",
        "created_by INTEGER",
        "is_active BOOLEAN DEFAULT 1",
        "deleted_at TIMESTAMP",
        "deleted_by INTEGER"
    ]
    
    for column in columns_to_add:
        column_name = column.split()[0]
        try:
            # Execute one ALTER statement at a time
            cursor.execute(f"ALTER TABLE company_tenders ADD COLUMN {column};")
            print(f"✓ Added column: {column_name}")
        except sqlite3.OperationalError:
            # This handles columns that already exist
            print(f"⚠ Column already exists: {column_name}")
   
    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == "__main__":
    update_columns()