# restore_backup.py
import sqlite3
import os
from datetime import datetime

def restore_database():
    backup_file = "data/backup/tender_system_dump_20260614_085255.sql"
    db_file = "data/tender_system.db"
    
    if not os.path.exists(backup_file):
        print("❌ Backup file not found!")
        return
    
    # Backup current database if it exists
    if os.path.exists(db_file):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_current = f"data/backup/tender_system_before_restore_{timestamp}.db"
        os.rename(db_file, backup_current)
        print(f"📦 Current database backed up to: {backup_current}")
    
    # Restore from SQL dump
    try:
        print("🔄 Restoring database from backup...")
        
        # Read the SQL file
        with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
            sql_script = f.read()
        
        # Connect to new database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Execute the SQL script
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        
        print("✅ Database restored successfully!")
        
        # Verify the restoration
        verify_database(db_file)
        
    except Exception as e:
        print(f"❌ Error restoring database: {e}")
        import traceback
        traceback.print_exc()

def verify_database(db_file):
    """Verify the restored database has data"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\n📊 Tables in restored database:")
    table_counts = {}
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table_counts[table_name] = count
            print(f"   - {table_name}: {count} rows")
        except:
            print(f"   - {table_name}: (error counting)")
    
    # Check users specifically
    try:
        cursor.execute("SELECT id, username, email, role FROM users")
        users = cursor.fetchall()
        print(f"\n👥 Users ({len(users)}):")
        for user in users:
            print(f"   - {user[1]} ({user[2]}) - {user[3]}")
    except Exception as e:
        print(f"\n❌ Error reading users: {e}")
    
    # Check companies
    try:
        cursor.execute("SELECT id, company_name, company_id FROM companies")
        companies = cursor.fetchall()
        print(f"\n🏢 Companies ({len(companies)}):")
        for company in companies:
            print(f"   - {company[1]} ({company[2]})")
    except Exception as e:
        print(f"\n❌ Error reading companies: {e}")
    
    conn.close()
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"   Total tables: {len(tables)}")
    total_rows = sum(table_counts.values())
    print(f"   Total rows: {total_rows:,}")

if __name__ == "__main__":
    restore_database()