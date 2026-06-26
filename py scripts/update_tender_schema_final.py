# update_tender_schema_final.py
import sqlite3

def update_tender_schema_final():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(company_tenders)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # All columns needed
    new_columns = {
        'app_id': 'TEXT',
        'package_no': 'TEXT',
        'project_code': 'TEXT',
        'project_name': 'TEXT',
        'procurement_nature': 'TEXT',
        'procurement_method': 'TEXT',
        'budget_type': 'TEXT',
        'source_of_funds': 'TEXT',
        'invitation_ref_no': 'TEXT',
        'procuring_entity_code': 'TEXT',
        'procuring_entity_district': 'TEXT',
        'tender_publication_date': 'TIMESTAMP',
        'document_selling_end_date': 'TIMESTAMP',
        'pre_bid_meeting_start': 'TIMESTAMP',
        'pre_bid_meeting_end': 'TIMESTAMP',
        'bid_opening_date': 'TIMESTAMP',
        'bid_opening_time': 'TEXT',
        'security_submission_deadline': 'TIMESTAMP',
        'eligibility_criteria': 'TEXT',
        'mode_of_payment': 'TEXT',
        'tender_document_price': 'REAL',
        'category': 'TEXT',
        'project_duration_months': 'INTEGER',
        'site_visit_required': 'BOOLEAN DEFAULT 0',
        'terms_and_conditions': 'TEXT'
    }
    
    for col_name, col_type in new_columns.items():
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
    update_tender_schema_final()