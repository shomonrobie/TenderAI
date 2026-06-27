# migrations/v024_add_oauth_support.py
import logging
import sqlite3
import os

logger = logging.getLogger(__name__)

class MigrationV024:
    """Migration v024: Add OAuth support columns for Google, Facebook, etc."""
    
    def __init__(self, db_crud=None):
        self.db = db_crud
        # Try multiple possible paths
        possible_paths = [
            "data/tender_system.db",
            "../data/tender_system.db",
            os.path.join(os.path.dirname(__file__), '..', 'data', 'tender_system.db'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'tender_system.db'),
        ]
        
        self.db_path = None
        for path in possible_paths:
            if os.path.exists(path):
                self.db_path = path
                break
        
        if not self.db_path:
            self.db_path = "data/tender_system.db"
        
        logger.info(f"📁 Using database: {self.db_path}")
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v024: Add OAuth support columns")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check existing columns in users table
            cursor.execute("PRAGMA table_info(users)")
            rows = cursor.fetchall()
            existing_columns = [row[1] for row in rows if row]
            
            logger.info(f"📋 Existing columns in users table: {existing_columns}")
            
            # List of columns to add (without UNIQUE constraint to avoid issues)
            columns_to_add = [
                # Google OAuth
                ('google_id', 'TEXT'),  # Remove UNIQUE, will add via index
                
                # Facebook OAuth
                ('facebook_id', 'TEXT'),  # Remove UNIQUE, will add via index
            ]
            
            # Add each column if it doesn't exist
            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                        logger.info(f"  ✅ Added column: {column_name}")
                    except sqlite3.OperationalError as e:
                        logger.warning(f"  ⚠️ Could not add {column_name}: {e}")
                else:
                    logger.info(f"  ℹ️ Column {column_name} already exists")
            
            # Create oauth_providers table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oauth_providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_name TEXT NOT NULL UNIQUE,
                    client_id TEXT,
                    client_secret TEXT,
                    redirect_uri TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("  ✅ Created oauth_providers table")
            
            # Create user_oauth table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_oauth (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    provider_name TEXT NOT NULL,
                    provider_user_id TEXT NOT NULL,
                    provider_email TEXT,
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expiry TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(provider_name, provider_user_id)
                )
            """)
            logger.info("  ✅ Created user_oauth table")
            
            # Check and create indexes safely
            # Check if column exists before creating index
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'google_id' in columns:
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)")
                    logger.info("  ✅ Created index: idx_users_google_id")
                except sqlite3.OperationalError as e:
                    logger.warning(f"  ⚠️ Could not create index on google_id: {e}")
            else:
                logger.info("  ℹ️ Skipping idx_users_google_id - column doesn't exist")
            
            if 'facebook_id' in columns:
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_facebook_id ON users(facebook_id)")
                    logger.info("  ✅ Created index: idx_users_facebook_id")
                except sqlite3.OperationalError as e:
                    logger.warning(f"  ⚠️ Could not create index on facebook_id: {e}")
            else:
                logger.info("  ℹ️ Skipping idx_users_facebook_id - column doesn't exist")
            
            # Other indexes (these columns should exist)
            if 'auth_provider' in columns:
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider)")
                    logger.info("  ✅ Created index: idx_users_auth_provider")
                except sqlite3.OperationalError as e:
                    logger.warning(f"  ⚠️ Could not create index on auth_provider: {e}")
            
            # Indexes on user_oauth table
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_oauth_user_id ON user_oauth(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_oauth_provider ON user_oauth(provider_name, provider_user_id)")
                logger.info("  ✅ Created indexes on user_oauth table")
            except sqlite3.OperationalError as e:
                logger.warning(f"  ⚠️ Could not create indexes on user_oauth: {e}")
            
            # Insert default OAuth providers if they don't exist
            default_providers = [
                ('google', '', '', '', 1),
                ('facebook', '', '', '', 1),
                ('github', '', '', '', 1),
                ('linkedin', '', '', '', 1),
            ]
            
            for provider_name, client_id, client_secret, redirect_uri, is_active in default_providers:
                cursor.execute("""
                    INSERT OR IGNORE INTO oauth_providers 
                    (provider_name, client_id, client_secret, redirect_uri, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, (provider_name, client_id, client_secret, redirect_uri, is_active))
            
            logger.info("  ✅ Inserted default OAuth providers")
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Migration v024 completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration v024 failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def down(self) -> bool:
        """Rollback the migration (limited support)"""
        logger.info("⚠️ Rolling back migration v024")
        logger.info("  ℹ️ SQLite doesn't support DROP COLUMN. Columns will remain.")
        logger.info("  ℹ️ You can drop tables if needed: DROP TABLE IF EXISTS oauth_providers")
        return True

# Standalone function for easy import
def run_migration(db_crud=None):
    """Run the migration"""
    migration = MigrationV024(db_crud)
    return migration.up()

if __name__ == "__main__":
    # Run directly
    success = run_migration()
    if success:
        print("✅ Migration v024 applied successfully")
    else:
        print("❌ Migration v024 failed")