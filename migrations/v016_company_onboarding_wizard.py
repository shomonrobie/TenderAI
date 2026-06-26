# migrations/v016_company_onboarding_wizard.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV016:
    """Migration v016: Company Onboarding Wizard"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v016: Company Onboarding Wizard")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Create onboarding wizard session table
                self._create_wizard_sessions(cursor)
                
                # 2. Create cost profile configuration table
                self._create_cost_profiles(cursor)
                
                # 3. Add onboarding columns to users table
                self._add_user_onboarding_columns(cursor)
                
                # 4. Create indexes
                self._create_indexes(cursor)
                
                conn.commit()
                logger.info("✅ Migration v016 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v016 failed: {e}")
            return False
    
    def _create_wizard_sessions(self, cursor):
        """Create table to track onboarding wizard sessions"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_wizard_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                step INTEGER DEFAULT 1,
                step_data TEXT,  -- JSON data for current step
                total_steps INTEGER DEFAULT 4,
                completed BOOLEAN DEFAULT 0,
                abandoned BOOLEAN DEFAULT 0,
                data_source_chosen TEXT,
                cost_profile_config TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: onboarding_wizard_sessions")
    
    def _create_cost_profiles(self, cursor):
        """Create table for company cost profile configuration"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_cost_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL UNIQUE,
                profile_name TEXT DEFAULT 'Default',
                economy_discount REAL DEFAULT 22.0,
                market_discount REAL DEFAULT 18.0,
                premium_discount REAL DEFAULT 14.0,
                markup_percentage REAL DEFAULT 15.0,
                overhead_percentage REAL DEFAULT 10.0,
                profit_margin_percentage REAL DEFAULT 15.0,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: company_cost_profiles")
    
    def _add_user_onboarding_columns(self, cursor):
        """Add onboarding columns to users table"""
        
        columns = [
            ('onboarding_completed', 'BOOLEAN DEFAULT 0'),
            ('onboarding_step', 'INTEGER DEFAULT 0'),
            ('onboarding_last_seen', 'TIMESTAMP'),
        ]
        
        for column, column_type in columns:
            if not self.db.column_exists('users', column):
                try:
                    sql = f"ALTER TABLE users ADD COLUMN {column} {column_type}"
                    cursor.execute(sql)
                    logger.info(f"  ✅ Added column: users.{column}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not add users.{column}: {e}")
            else:
                logger.info(f"  ℹ️ Column already exists: users.{column}")
    
    def _create_indexes(self, cursor):
        """Create indexes for performance"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_wizard_company ON onboarding_wizard_sessions(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_wizard_user ON onboarding_wizard_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_wizard_status ON onboarding_wizard_sessions(completed, abandoned)",
            "CREATE INDEX IF NOT EXISTS idx_cost_profile_company ON company_cost_profiles(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_cost_profile_active ON company_cost_profiles(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_users_onboarding ON users(onboarding_completed, onboarding_step)",
        ]
        
        for idx in indexes:
            try:
                cursor.execute(idx)
                logger.info(f"  ✅ Created index: {idx.split('ON')[1].strip().split('(')[0]}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not create index: {e}")
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v016")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                tables = ['onboarding_wizard_sessions', 'company_cost_profiles']
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"  ✅ Dropped table: {table}")
                
                logger.info("  ℹ️ Onboarding columns will remain (SQLite doesn't support DROP COLUMN)")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False