# update_db_schema_complete.py
import sqlite3

def update_schema():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Add missing columns to historical_tenders
    columns_to_add = [
        ("winning_company_type", "TEXT"),
        ("our_awarded_price", "REAL")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE historical_tenders ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added {col_name} column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"⚠ Column {col_name} already exists")
            else:
                print(f"Error adding {col_name}: {e}")
    
    # Create company_nppi table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS company_nppi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        procurement_type TEXT,
        nppi_factor REAL,
        data_points INTEGER,
        calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id)
    )
    ''')
    print("✓ company_nppi table verified")
    
    conn.commit()
    conn.close()
    print("Database schema update complete!")

if __name__ == "__main__":
    update_schema()