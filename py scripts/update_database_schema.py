"""
Database Schema Update Script
Adds historical tenders and company NPPI tables
Run this once to update your database
"""

import sqlite3
import os
from datetime import datetime

def update_database_schema():
    """Add new tables to existing database"""
    
    db_path = "data/tender_system.db"
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Creating new database...")
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Updating Database Schema for Historical Data Management")
    print("=" * 60)
    
    # 1. Create historical_tenders table
    print("\n1. Creating historical_tenders table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historical_tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        company_id INTEGER,
        tender_id TEXT,
        tender_title TEXT,
        procuring_entity TEXT,
        procurement_type TEXT,
        official_estimate REAL,
        awarded_price REAL,
        num_competitors INTEGER,
        award_date DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (company_id) REFERENCES companies (id)
    )
    ''')
    print("   ✓ historical_tenders table created")
    
    # 2. Create company_nppi table
    print("\n2. Creating company_nppi table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS company_nppi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        procurement_type TEXT,
        nppi_factor REAL,
        data_points INTEGER,
        calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id),
        UNIQUE(company_id, procurement_type, calculation_date)
    )
    ''')
    print("   ✓ company_nppi table created")
    
    # 3. Create indexes for better performance
    print("\n3. Creating indexes...")
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_historical_company 
    ON historical_tenders(company_id, procurement_type, award_date)
    ''')
    print("   ✓ Index on historical_tenders (company_id, procurement_type, award_date)")
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_nppi_company 
    ON company_nppi(company_id, procurement_type, calculation_date)
    ''')
    print("   ✓ Index on company_nppi (company_id, procurement_type, calculation_date)")
    
    # 4. Add sample historical data for demonstration (optional)
    print("\n4. Adding sample historical data (for testing)...")
    
    # Check if there's any data already
    cursor.execute("SELECT COUNT(*) FROM historical_tenders")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Get company IDs
        cursor.execute("SELECT id FROM companies WHERE company_name != 'System Admin' LIMIT 1")
        company = cursor.fetchone()
        
        if company:
            company_id = company[0]
            
            # Get user ID for that company
            cursor.execute("SELECT id FROM users WHERE company_id = ? LIMIT 1", (company_id,))
            user = cursor.fetchone()
            
            if user:
                user_id = user[0]
                
                # Sample historical tenders
                sample_data = [
                    (user_id, company_id, "TND-G-2024-001", "Office Equipment Supply", "PWD", "goods", 
                     5000000, 4600000, 8, "2024-01-15", "Standard procurement"),
                    (user_id, company_id, "TND-W-2024-002", "Road Construction", "RHD", "works", 
                     15000000, 13800000, 12, "2024-02-20", "Competitive bidding"),
                    (user_id, company_id, "TND-S-2024-003", "Consultancy Services", "LGED", "services", 
                     3000000, 2850000, 5, "2024-03-10", "Technical evaluation"),
                    (user_id, company_id, "TND-G-2024-004", "Computer Hardware", "DPE", "goods", 
                     8000000, 7400000, 10, "2024-04-05", "Bulk procurement"),
                    (user_id, company_id, "TND-W-2024-005", "Bridge Maintenance", "Bridge Division", "works", 
                     25000000, 22750000, 15, "2024-05-12", "Major project"),
                ]
                
                cursor.executemany('''
                INSERT INTO historical_tenders (
                    user_id, company_id, tender_id, tender_title, procuring_entity,
                    procurement_type, official_estimate, awarded_price, num_competitors,
                    award_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', sample_data)
                
                print(f"   ✓ Added {len(sample_data)} sample historical tenders for company ID {company_id}")
                
                # Calculate and save initial NPPI values
                print("\n5. Calculating initial NPPI values...")
                
                for ptype in ['goods', 'works', 'services']:
                    # Get data for this procurement type
                    cursor.execute('''
                    SELECT official_estimate, awarded_price 
                    FROM historical_tenders 
                    WHERE company_id = ? AND procurement_type = ?
                    ''', (company_id, ptype))
                    
                    data = cursor.fetchall()
                    
                    if len(data) >= 3:
                        deviations = []
                        for row in data:
                            if row[0] and row[0] > 0:
                                deviation = (row[1] - row[0]) / row[0]
                                deviations.append(deviation)
                        
                        if deviations:
                            import numpy as np
                            median_deviation = np.median(deviations)
                            nppi_factor = 1 + median_deviation
                            
                            cursor.execute('''
                            INSERT INTO company_nppi (company_id, procurement_type, nppi_factor, data_points)
                            VALUES (?, ?, ?, ?)
                            ''', (company_id, ptype, round(nppi_factor, 4), len(data)))
                            
                            print(f"   ✓ {ptype.upper()} NPPI: {nppi_factor:.4f} (based on {len(data)} tenders)")
                    else:
                        print(f"   ⚠ {ptype.upper()}: Insufficient data (need at least 3 tenders)")
            else:
                print("   ⚠ No users found, skipping sample data")
        else:
            print("   ⚠ No companies found, skipping sample data")
    else:
        print(f"   ℹ Database already has {count} historical records, skipping sample data")
    
    # Commit changes
    conn.commit()
    
    # Verify tables were created
    print("\n" + "=" * 60)
    print("VERIFICATION - Existing Tables:")
    print("=" * 60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        row_count = cursor.fetchone()[0]
        print(f"  ✓ {table[0]}: {row_count} rows")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ DATABASE SCHEMA UPDATE COMPLETE!")
    print("=" * 60)
    print("\nNew tables added:")
    print("  - historical_tenders: Store past tender results")
    print("  - company_nppi: Cache company-specific NPPI values")
    print("\nYou can now use the Historical Data Management feature.")

def verify_database():
    """Verify the database structure"""
    db_path = "data/tender_system.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)
    
    # Check new tables
    required_tables = ['historical_tenders', 'company_nppi']
    
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count} rows")
        else:
            print(f"❌ {table}: NOT FOUND")
    
    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    print(f"\n📊 Indexes: {len(indexes)}")
    
    conn.close()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DATABASE SCHEMA UPDATE UTILITY")
    print("=" * 60)
    print("\nThis script will add historical data tables to your database.")
    print("It is safe to run even if tables already exist.\n")
    
    confirm = input("Do you want to proceed? (y/n): ")
    
    if confirm.lower() == 'y':
        update_database_schema()
        verify_database()
    else:
        print("Operation cancelled.")