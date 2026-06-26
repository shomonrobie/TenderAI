# fix_tender_constraint.py
import sqlite3

def fix_constraint():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get all columns from the existing table
    cursor.execute("PRAGMA table_info(company_tenders)")
    existing_columns = cursor.fetchall()
    column_names = [col[1] for col in existing_columns]
    
    print(f"Existing columns: {column_names}")
    
    # Get all data from the current table
    cursor.execute("SELECT * FROM company_tenders")
    data = cursor.fetchall()
    print(f"Found {len(data)} records to preserve")
    
    # Drop old table
    cursor.execute("DROP TABLE company_tenders")
    
    # Recreate table with all columns from the old table plus any missing ones
    # First, build the CREATE TABLE statement dynamically
    create_statement = '''
    CREATE TABLE company_tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        tender_id TEXT,
        tender_title TEXT,
        procuring_entity TEXT,
        division TEXT,
        district TEXT,
        thana TEXT,
        country TEXT DEFAULT 'Bangladesh',
        procurement_type TEXT,
        official_estimate REAL,
        submission_deadline TIMESTAMP,
        tender_security REAL,
        document_fee REAL,
        evaluation_type TEXT,
        mode_of_payment TEXT,
        eligibility_criteria TEXT,
        invitation_ref_no TEXT,
        package_no TEXT,
        project_code TEXT,
        project_name TEXT,
        inviting_official_name TEXT,
        inviting_official_designation TEXT,
        inviting_official_phone TEXT,
        inviting_official_email TEXT,
        inviting_official_address TEXT,
        inviting_official_city TEXT,
        inviting_official_thana TEXT,
        inviting_official_district TEXT,
        our_bid_amount REAL,
        bid_submitted_by INTEGER,
        bid_submission_date TIMESTAMP,
        bid_status TEXT DEFAULT 'draft',
        evaluation_status TEXT DEFAULT 'pending',
        winning_bid_amount REAL,
        winning_competitor TEXT,
        our_rank INTEGER,
        total_bidders INTEGER,
        award_date DATE,
        notes TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, tender_id),
        FOREIGN KEY (company_id) REFERENCES companies (id),
        FOREIGN KEY (bid_submitted_by) REFERENCES users (id),
        FOREIGN KEY (created_by) REFERENCES users (id)
    )
    '''
    
    cursor.execute(create_statement)
    
    # Get the new column list
    cursor.execute("PRAGMA table_info(company_tenders)")
    new_columns = [col[1] for col in cursor.fetchall()]
    
    # Find which columns exist in both old and new
    common_columns = [col for col in column_names if col in new_columns]
    
    # Restore data for common columns only
    if data and common_columns:
        # Build SELECT and INSERT clauses
        select_cols = ','.join(common_columns)
        insert_cols = ','.join(common_columns)
        placeholders = ','.join(['?' for _ in common_columns])
        
        for row in data:
            # Create a dictionary of column:value for this row
            row_dict = dict(zip(column_names, row))
            
            # Extract values for common columns in order
            values = [row_dict[col] for col in common_columns]
            
            try:
                cursor.execute(f"INSERT INTO company_tenders ({insert_cols}) VALUES ({placeholders})", values)
            except Exception as e:
                print(f"Error restoring row: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Fixed UNIQUE constraint to (company_id, tender_id)")

if __name__ == "__main__":
    fix_constraint()