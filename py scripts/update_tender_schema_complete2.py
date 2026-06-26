# update_tender_schema_complete.py
import sqlite3

def update_tender_schema_complete():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(company_tenders)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # Complete list of all columns needed
    all_columns = {
        # Basic Information
        'tender_id': 'TEXT',
        'app_id': 'TEXT',
        'tender_title': 'TEXT',
        'procuring_entity': 'TEXT',
        'procuring_entity_code': 'TEXT',
        'procuring_entity_district': 'TEXT',
        'ministry': 'TEXT',
        'organization': 'TEXT',
        'division': 'TEXT',
        'district': 'TEXT',
        'thana': 'TEXT',
        'country': 'TEXT',
        
        # Procurement Details
        'procurement_nature': 'TEXT',
        'procurement_type': 'TEXT',
        'event_type': 'TEXT',
        'procurement_method': 'TEXT',
        'budget_type': 'TEXT',
        'source_of_funds': 'TEXT',
        'invitation_for': 'TEXT',
        'invitation_ref_no': 'TEXT',
        
        # Project Details
        'project_code': 'TEXT',
        'project_name': 'TEXT',
        'package_no': 'TEXT',
        'package_description': 'TEXT',
        'category': 'TEXT',
        
        # Financial Information
        'official_estimate': 'REAL',
        'tender_security': 'REAL',
        'document_fee': 'REAL',
        
        # Schedule Information
        'tender_publication_date': 'TIMESTAMP',
        'document_selling_end_date': 'TIMESTAMP',
        'pre_bid_meeting_start': 'TIMESTAMP',
        'pre_bid_meeting_end': 'TIMESTAMP',
        'submission_deadline': 'TIMESTAMP',
        'security_submission_deadline': 'TIMESTAMP',
        'bid_opening_date': 'TIMESTAMP',
        'bid_opening_time': 'TEXT',
        'security_valid_upto': 'DATE',
        'tender_valid_upto': 'DATE',
        
        # Evaluation
        'evaluation_type': 'TEXT',
        'eligibility_criteria': 'TEXT',
        'mode_of_payment': 'TEXT',
        
        # Official Contact
        'inviting_official_name': 'TEXT',
        'inviting_official_designation': 'TEXT',
        'inviting_official_address': 'TEXT',
        'inviting_official_phone': 'TEXT',
        'inviting_official_fax': 'TEXT',
        'inviting_official_email': 'TEXT',
        'inviting_official_city': 'TEXT',
        'inviting_official_thana': 'TEXT',
        'inviting_official_district': 'TEXT',
        
        # Additional
        'pre_bid_meeting_venue': 'TEXT',
        'site_visit_required': 'BOOLEAN DEFAULT 0',
        'project_duration_months': 'INTEGER',
        'notes': 'TEXT'
    }
    
    # Add missing columns
    for col_name, col_type in all_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE company_tenders ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
    
    # Create tender_lots table if not exists
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
    print("✓ tender_lots table verified")
    
    conn.commit()
    conn.close()
    print("\n✅ Database schema update completed!")

if __name__ == "__main__":
    update_tender_schema_complete()
