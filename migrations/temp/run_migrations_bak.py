# migrations/run_migrations.py

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


class MigrationManager:
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
    
    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY id")
        applied = [row[0] for row in cursor.fetchall()]
        conn.close()
        return set(applied)
    
    def mark_migration_applied(self, version, name, success=True):
        """Mark a migration as applied"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO schema_migrations (version, name, success)
            VALUES (?, ?, ?)
        """, (version, name, success))
        conn.commit()
        conn.close()
    
    def is_table_exists(self, table_name):
        """Check if a table exists in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def run_migration(self, migration_module):
        """Run a single migration with safety checks"""
        try:
            # Check if migration already applied
            if hasattr(migration_module, 'version'):
                applied = self.get_applied_migrations()
                if migration_module.version in applied:
                    print(f"⏭️  Skipping {migration_module.version} - already applied")
                    return True
            
            print(f"📦 Running migration: {migration_module.__name__}")
            
            # Run the migration
            if hasattr(migration_module, 'upgrade'):
                migration_module.upgrade(self.db_path)
            elif hasattr(migration_module, 'up'):
                migration_module.up(self.db_path)
            else:
                raise AttributeError(f"No upgrade/up method found in {migration_module.__name__}")
            
            # Mark as applied
            self.mark_migration_applied(migration_module.version, migration_module.__name__)
            print(f"✅ Successfully applied {migration_module.version}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply {getattr(migration_module, 'version', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_migrations(self):
        """Run all pending migrations in order"""
        
        # Import all migration modules
        migrations = []
        
        # Try to import each migration (some may not exist yet)
        migration_files = [
            'v001_initial_schema',
            'v002_add_subscription_permissions', 
            'v003_add_rate_chapters_sections',
            'v004_add_company_subscriptions',
            'v006_boq_tables',
            'v007_scenarion_tables',
            'v008_extension_tables',
            'v009_knowledge_repository',
            'v010_fix_companies_table',
            'v011_add_company_columns'
        ]
        
        for migration_name in migration_files:
            try:
                migration = __import__(migration_name)
                migrations.append(migration)
                print(f"  Loaded: {migration_name}")
            except ImportError as e:
                print(f"  ⚠️ Migration {migration_name} not found: {e}")
        
        if not migrations:
            print("  No migrations found")
            return True
        
        applied = self.get_applied_migrations()
        pending_count = 0
        failed = False
        
        for migration in migrations:
            if hasattr(migration, 'version'):
                if migration.version not in applied:
                    print(f"\n📦 Pending migration: {migration.version}")
                    pending_count += 1
                    if not self.run_migration(migration):
                        failed = True
                        break
                else:
                    print(f"⏭️  {migration.version} already applied")
            else:
                print(f"⚠️ Skipping {migration.__name__} - no version attribute")
        
        print("\n" + "="*50)
        if failed:
            print("❌ Migration failed! Please check the error above.")
            return False
        elif pending_count == 0:
            print("✅ No pending migrations. Database is up to date!")
        else:
            print(f"✅ Successfully applied {pending_count} migration(s)!")
        print("="*50)
        
        return True


# For backward compatibility with existing code
def run_migrations(db_path="data/tender_system.db"):
    """Legacy function for compatibility"""
    manager = MigrationManager(db_path)
    return manager.run_all_migrations()


if __name__ == "__main__":
    # When run directly, execute migrations
    manager = MigrationManager()
    success = manager.run_all_migrations()
    sys.exit(0 if success else 1)