# fix_tender_schema.py
import sqlite3

def fix_tender_schema():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(company_tenders)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # Columns to add if missing
    columns_to_add = {
        'created_by': 'INTEGER',
        'updated_by': 'INTEGER',
        'bid_submitted_by': 'INTEGER',
        'bid_submission_date': 'TIMESTAMP',
        'evaluation_status': 'TEXT DEFAULT pending',
        'winning_bid_amount': 'REAL',
        'winning_competitor': 'TEXT',
        'our_rank': 'INTEGER',
        'total_bidders': 'INTEGER',
        'award_date': 'DATE'
    }
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE company_tenders ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"⚠ Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    print("\n✅ Database schema update completed!")

if __name__ == "__main__":
    fix_tender_schema()