# update_analysis_schema.py
import sqlite3

def update_analysis_schema():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Get existing columns in tender_analyses
    cursor.execute("PRAGMA table_info(tender_analyses)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # Columns to add if missing
    columns_to_add = {
        'division': 'TEXT',
        'district': 'TEXT',
        'thana': 'TEXT',
        'procuring_entity': 'TEXT',
        'competitor_bids': 'TEXT',  # JSON format to store competitor bids
        'risk_strategy': 'TEXT',
        'confidence_score': 'REAL',
        'expected_profit': 'REAL',
        'expected_value': 'REAL',
        'slt_threshold': 'REAL',
        'nppi_factor': 'REAL',
        'weighted_average': 'REAL',
        'user_id': 'INTEGER',  # Ensure user_id exists for permission checks
        'company_id': 'INTEGER'  # Ensure company_id exists for multi-tenant isolation
    }
    
    print("Updating tender_analyses table...")
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE tender_analyses ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"⚠ Column already exists: {col_name}")
    
    # Create indexes for better query performance
    print("\nCreating indexes...")
    
    # Index for user-based queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user ON tender_analyses(user_id)")
    print("✓ Created index: idx_analyses_user")
    
    # Index for company-based queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_company ON tender_analyses(company_id)")
    print("✓ Created index: idx_analyses_company")
    
    # Index for date-based queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_date ON tender_analyses(analysis_date)")
    print("✓ Created index: idx_analyses_date")
    
    # Index for status-based queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_status ON tender_analyses(bid_status)")
    print("✓ Created index: idx_analyses_status")
    
    conn.commit()
    
    # Verify the table structure
    print("\n" + "=" * 50)
    print("FINAL TABLE STRUCTURE - tender_analyses")
    print("=" * 50)
    
    cursor.execute("PRAGMA table_info(tender_analyses)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    
    conn.close()
    print("\n✅ Database schema update completed!")

if __name__ == "__main__":
    update_analysis_schema()
