# migrations/safe_migrate.py
"""
Safe database migration with backup and data import.
Creates a new database with correct schema and migrates existing data.
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.schema import DatabaseSchema


class SafeMigrator:
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        self.backup_path = None
        self.new_db_path = None
        
    def create_backup(self):
        """Create timestamped backup of current database"""
        if not os.path.exists(self.db_path):
            print(f"⚠️ No existing database found at {self.db_path}")
            return False
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = f"data/backup/tender_system_backup_{timestamp}.db"
        
        # Create backup directory if not exists
        Path("data/backup").mkdir(parents=True, exist_ok=True)
        
        # Copy database
        shutil.copy2(self.db_path, self.backup_path)
        print(f"✅ Database backed up to: {self.backup_path}")
        
        # Also create SQL dump for extra safety
        self.create_sql_dump(timestamp)
        
        return True
    
    def create_sql_dump(self, timestamp):
        """Create SQL dump of current database"""
        dump_path = f"data/backup/tender_system_dump_{timestamp}.sql"
        
        conn = sqlite3.connect(self.db_path)
        with open(dump_path, 'w', encoding='utf-8') as f:
            for line in conn.iterdump():
                f.write(f'{line}\n')
        conn.close()
        
        print(f"✅ SQL dump created: {dump_path}")
    
    def get_existing_data(self):
        """Extract all data from current database"""
        if not os.path.exists(self.db_path):
            print("No existing database to migrate")
            return {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        data = {}
        
        for table in tables:
            try:
                # Get all data from table
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                data[table] = [dict(row) for row in rows]
                print(f"  📦 Extracted {len(rows)} rows from {table}")
            except Exception as e:
                print(f"  ⚠️ Could not extract {table}: {e}")
                data[table] = []
        
        conn.close()
        return data
    
    def create_new_database(self):
        """Create new database with fresh schema"""
        self.new_db_path = "data/tender_system_new.db"
        
        # Remove existing new db if exists
        if os.path.exists(self.new_db_path):
            os.remove(self.new_db_path)
        
        # Create fresh database with correct schema
        schema = DatabaseSchema(self.new_db_path)
        schema.create_all_tables()
        schema.insert_default_data()
        
        print(f"✅ New database created with fresh schema: {self.new_db_path}")
        return True
    
    def migrate_data(self, old_data):
        """Migrate data from old database to new database"""
        if not old_data:
            print("No data to migrate")
            return False
        
        conn_new = sqlite3.connect(self.new_db_path)
        cursor_new = conn_new.cursor()
        
        # Get columns in new database
        cursor_new.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        new_tables = {row[0] for row in cursor_new.fetchall()}
        
        migrated_count = 0
        skipped_count = 0
        
        for table_name, rows in old_data.items():
            if table_name not in new_tables:
                print(f"  ⏭️ Skipping {table_name} (not in new schema)")
                skipped_count += 1
                continue
            
            if not rows:
                continue
            
            # Get columns in new table
            cursor_new.execute(f"PRAGMA table_info({table_name})")
            new_columns = {row[1] for row in cursor_new.fetchall()}
            
            # Filter rows to only include columns that exist in new table
            successful = 0
            for row in rows:
                # Filter row data to only columns that exist in new table
                filtered_row = {k: v for k, v in row.items() if k in new_columns}
                
                if filtered_row:
                    columns = ', '.join(filtered_row.keys())
                    placeholders = ', '.join(['?' for _ in filtered_row])
                    values = list(filtered_row.values())
                    
                    try:
                        cursor_new.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
                        successful += 1
                    except Exception as e:
                        print(f"    ⚠️ Failed to insert row in {table_name}: {e}")
            
            if successful > 0:
                print(f"  ✅ Migrated {successful}/{len(rows)} rows to {table_name}")
                migrated_count += 1
        
        conn_new.commit()
        conn_new.close()
        
        print(f"\n📊 Migration summary: {migrated_count} tables migrated, {skipped_count} skipped")
        return True
    
    def add_defaults_for_missing_columns(self):
        """Add default values for new required columns"""
        conn = sqlite3.connect(self.new_db_path)
        cursor = conn.cursor()
        
        print("\n🔧 Setting default values for new columns...")
        
        # For users table - set default values for new columns
        try:
            # Set default mobile_number for existing users (if null)
            cursor.execute("""
                UPDATE users 
                SET mobile_number = '01' || substr(cast(abs(random()) as text), 1, 9)
                WHERE mobile_number IS NULL OR mobile_number = ''
            """)
            print(f"  ✅ Set default mobile_number for {cursor.rowcount} users")
            
            # Set default values for boolean fields
            cursor.execute("UPDATE users SET mobile_verified = 0 WHERE mobile_verified IS NULL")
            cursor.execute("UPDATE users SET email_verified = 0 WHERE email_verified IS NULL")
            cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
            cursor.execute("UPDATE users SET is_approved = 1 WHERE is_approved IS NULL")
            print("  ✅ Set default boolean values")
            
        except Exception as e:
            print(f"  ⚠️ Could not set defaults for users: {e}")
        
        # For companies table
        try:
            cursor.execute("""
                UPDATE companies 
                SET mobile_number = '01' || substr(cast(abs(random()) as text), 1, 9)
                WHERE mobile_number IS NULL OR mobile_number = ''
            """)
            print(f"  ✅ Set default mobile_number for {cursor.rowcount} companies")
            
        except Exception as e:
            print(f"  ⚠️ Could not set defaults for companies: {e}")
        
        conn.commit()
        conn.close()
    
    def verify_migration(self):
        """Verify that migration was successful"""
        print("\n" + "="*60)
        print("🔍 VERIFYING MIGRATION")
        print("="*60)
        
        conn_old = None
        conn_new = None
        
        try:
            # Check if old db exists
            old_exists = os.path.exists(self.db_path)
            new_exists = os.path.exists(self.new_db_path)
            
            print(f"  Old database exists: {old_exists}")
            print(f"  New database exists: {new_exists}")
            
            if not new_exists:
                print("❌ New database not found!")
                return False
            
            # Compare table counts
            conn_new = sqlite3.connect(self.new_db_path)
            cursor_new = conn_new.cursor()
            cursor_new.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            new_table_count = cursor_new.fetchone()[0]
            
            print(f"  Tables in new database: {new_table_count}")
            
            # Check critical columns
            cursor_new.execute("PRAGMA table_info(users)")
            user_columns = {row[1] for row in cursor_new.fetchall()}
            
            required_columns = ['mobile_number', 'mobile_verified', 'email_verified']
            missing = [c for c in required_columns if c not in user_columns]
            
            if missing:
                print(f"  ❌ Missing columns in users: {missing}")
                return False
            else:
                print("  ✅ All required columns present in users table")
            
            # Check user count
            cursor_new.execute("SELECT COUNT(*) FROM users")
            user_count = cursor_new.fetchone()[0]
            print(f"  Users in new database: {user_count}")
            
            print("\n✅ Migration verification successful!")
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
        finally:
            if conn_old:
                conn_old.close()
            if conn_new:
                conn_new.close()
    
    def replace_database(self):
        """Replace old database with new one"""
        print("\n" + "="*60)
        print("🔄 REPLACING DATABASE")
        print("="*60)
        
        # Rename old database (keep as backup)
        if os.path.exists(self.db_path):
            old_renamed = f"{self.db_path}.old"
            if os.path.exists(old_renamed):
                os.remove(old_renamed)
            os.rename(self.db_path, old_renamed)
            print(f"  Renamed old database to: {old_renamed}")
        
        # Rename new database to production name
        os.rename(self.new_db_path, self.db_path)
        print(f"  ✅ New database now active: {self.db_path}")
        
        return True
    
    def run(self, dry_run=False):
        """Run complete migration"""
        
        print("\n" + "="*70)
        print("🔄 SAFE DATABASE MIGRATION")
        print("="*70)
        print(f"Source: {self.db_path}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")
            print("   The following steps would be executed:\n")
            print("   1. Backup current database")
            print("   2. Extract data from current database")
            print("   3. Create new database with correct schema")
            print("   4. Migrate data to new database")
            print("   5. Add default values for new columns")
            print("   6. Verify migration")
            print("   7. Replace old database with new one")
            print("\n💡 To execute migration, run without --dry-run")
            return True
        
        # Step 1: Backup
        print("\n📦 Step 1: Creating backup...")
        if not self.create_backup():
            print("❌ Backup failed! Migration aborted.")
            return False
        
        # Step 2: Extract existing data
        print("\n📤 Step 2: Extracting existing data...")
        old_data = self.get_existing_data()
        
        # Step 3: Create new database
        print("\n🏗️ Step 3: Creating new database with fresh schema...")
        if not self.create_new_database():
            print("❌ Failed to create new database!")
            return False
        
        # Step 4: Migrate data
        print("\n🔄 Step 4: Migrating data...")
        if not self.migrate_data(old_data):
            print("⚠️ Some data may not have migrated, but continuing...")
        
        # Step 5: Add default values for new columns
        print("\n📝 Step 5: Adding default values...")
        self.add_defaults_for_missing_columns()
        
        # Step 6: Verify
        print("\n✅ Step 6: Verifying migration...")
        if not self.verify_migration():
            print("❌ Verification failed! Check the new database before replacing.")
            response = input("\nContinue with replacement anyway? (y/N): ")
            if response.lower() != 'y':
                print("Migration aborted. New database kept at: " + self.new_db_path)
                return False
        
        # Step 7: Replace database
        print("\n🔄 Step 7: Replacing database...")
        self.replace_database()
        
        print("\n" + "="*70)
        print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"\n📁 Backup saved at: {self.backup_path}")
        print("✅ Your database now has the complete schema with all required columns!")
        
        return True


def run_migration():
    """Run the migration"""
    # Check for --dry-run argument
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    
    migrator = SafeMigrator("data/tender_system.db")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE")
        migrator.run(dry_run=True)
    else:
        print("\n⚠️ WARNING: This will modify your database!")
        print("   A backup will be created before any changes.")
        response = input("\nDo you want to continue? (y/N): ")
        if response.lower() == 'y':
            migrator.run(dry_run=False)
        else:
            print("Migration cancelled.")


if __name__ == "__main__":
    run_migration()