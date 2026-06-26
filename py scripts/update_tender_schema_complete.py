# update_tender_schema_complete.py
import sqlite3
from datetime import datetime

def update_tender_schema():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Check existing columns in company_tenders
    cursor.execute("PRAGMA table_info(company_tenders)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # New columns to add
    new_columns = {
        'tender_security': 'REAL',
        'document_fee': 'REAL',
        'district': 'TEXT',
        'thana': 'TEXT',
        'country': 'TEXT DEFAULT "Bangladesh"',
        'tender_type': 'TEXT',
        'evaluation_type': 'TEXT',
        'lot_details': 'TEXT',  # JSON format for multiple lots
        'security_valid_upto': 'DATE',
        'tender_valid_upto': 'DATE',
        'inviting_official_name': 'TEXT',
        'inviting_official_designation': 'TEXT',
        'inviting_official_address': 'TEXT',
        'inviting_official_phone': 'TEXT',
        'inviting_official_email': 'TEXT',
        'tender_document_url': 'TEXT',
        'tender_notice_url': 'TEXT',
        'corrigendum_count': 'INTEGER DEFAULT 0',
        'pre_bid_meeting_date': 'TIMESTAMP',
        'pre_bid_meeting_venue': 'TEXT',
        'bid_opening_date': 'TIMESTAMP',
        'bid_opening_venue': 'TEXT'
    }
    
    # Add missing columns
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE company_tenders ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"⚠ Column already exists: {col_name}")
    
    # Create lot_details table for better lot management
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tender_lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        lot_no TEXT,
        lot_description TEXT,
        location TEXT,
        security_amount REAL,
        estimated_value REAL,
        start_date DATE,
        completion_date DATE,
        our_bid_amount REAL,
        bid_status TEXT,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id)
    )
    ''')
    print("✓ Created tender_lots table")
    
    # Create tender_documents table for storing PDF references
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tender_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        document_type TEXT,
        file_name TEXT,
        file_path TEXT,
        uploaded_by INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id)
    )
    ''')
    print("✓ Created tender_documents table")
    
    # Create tender_notifications table for reminders
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tender_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        notification_type TEXT,
        notification_date TIMESTAMP,
        sent BOOLEAN DEFAULT 0,
        sent_at TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id)
    )
    ''')
    print("✓ Created tender_notifications table")
    
    conn.commit()
    conn.close()
    print("\n✅ Database schema update completed successfully!")

if __name__ == "__main__":
    update_tender_schema()
