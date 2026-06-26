# migrations/v014_demo_data_framework.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV014:
    """Migration v014: Add demo data framework columns and tables"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v014: Demo Data Framework")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Add columns to existing tables
                self._add_demo_columns(cursor)
                
                # 2. Create demo data generation log table
                self._create_demo_generation_log(cursor)
                
                # 3. Create company onboarding status table
                self._create_onboarding_status(cursor)
                
                # 4. Add columns to companies table
                self._add_company_environment_columns(cursor)
                
                # 5. Create indexes
                self._create_indexes(cursor)
                
                conn.commit()
                logger.info("✅ Migration v014 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v014 failed: {e}")
            return False
    
    def _add_demo_columns(self, cursor):
        """Add is_demo and data_source_type columns to existing tables"""
        
        tables_and_columns = [
            ('tenant_rate_books', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('tenant_rate_books', 'environment_mode', "TEXT DEFAULT 'DEMO'"),
            ('tenant_rate_books', 'data_source_type', "TEXT DEFAULT 'DEMO'"),
            ('tenant_rate_versions', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('tenant_rate_items', 'master_chapter_number', 'TEXT'),
            ('tenant_rate_items', 'master_section_number', 'TEXT'),
            ('tenant_rate_items', 'master_item_code', 'TEXT'),
            ('tenant_rate_items', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('tenant_pricing_levels', 'base_rate', 'REAL'),
            ('tenant_pricing_levels', 'discount_percentage', 'REAL DEFAULT 0'),
            ('tenant_pricing_levels', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('boq_generation_history', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('boq_generation_history', 'data_source_type', "TEXT DEFAULT 'COMPANY'"),
            ('boq_items', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('tender_analyses', 'is_demo', 'BOOLEAN DEFAULT 0'),
            ('tender_analyses', 'data_source_type', "TEXT DEFAULT 'COMPANY'"),
        ]
        
        for table, column, column_type in tables_and_columns:
            if not self.db.column_exists(table, column):
                try:
                    sql = f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
                    cursor.execute(sql)
                    logger.info(f"  ✅ Added column: {table}.{column}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not add {table}.{column}: {e}")
            else:
                logger.info(f"  ℹ️ Column already exists: {table}.{column}")
    
    def _create_demo_generation_log(self, cursor):
        """Create table to track demo data generation"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS demo_data_generation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER,
                generation_type TEXT NOT NULL,  -- 'PWD', 'LGED', 'CUSTOM', 'ALL'
                items_generated INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: demo_data_generation_log")
    
    def _create_onboarding_status(self, cursor):
        """Create table to track company onboarding status"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_onboarding_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL UNIQUE,
                onboarding_step INTEGER DEFAULT 1,
                data_source_chosen TEXT,  -- 'DEMO', 'IMPORT', 'CLONE'
                demo_generated BOOLEAN DEFAULT 0,
                demo_generated_at TIMESTAMP,
                production_activated BOOLEAN DEFAULT 0,
                production_activated_at TIMESTAMP,
                onboarding_completed BOOLEAN DEFAULT 0,
                onboarding_completed_at TIMESTAMP,
                last_step_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        logger.info("  ✅ Created table: company_onboarding_status")
    
    def _add_company_environment_columns(self, cursor):
        """Add environment columns to companies table"""
        
        columns = [
            ('environment_mode', "TEXT DEFAULT 'DEMO'"),
            ('onboarding_status', "TEXT DEFAULT 'pending'"),  # pending, in_progress, completed
            ('demo_data_generated_at', 'TIMESTAMP'),
            ('production_activated_at', 'TIMESTAMP'),
        ]
        
        for column, column_type in columns:
            if not self.db.column_exists('companies', column):
                try:
                    sql = f"ALTER TABLE companies ADD COLUMN {column} {column_type}"
                    cursor.execute(sql)
                    logger.info(f"  ✅ Added column: companies.{column}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not add companies.{column}: {e}")
            else:
                logger.info(f"  ℹ️ Column already exists: companies.{column}")
    
    def _create_indexes(self, cursor):
        """Create indexes for performance"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_demo_log_company ON demo_data_generation_log(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_demo_log_status ON demo_data_generation_log(status)",
            "CREATE INDEX IF NOT EXISTS idx_onboarding_company ON company_onboarding_status(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_onboarding_status ON company_onboarding_status(onboarding_step)",
            "CREATE INDEX IF NOT EXISTS idx_tenant_books_demo ON tenant_rate_books(is_demo, environment_mode)",
            "CREATE INDEX IF NOT EXISTS idx_tenant_items_demo ON tenant_rate_items(is_demo)",
            "CREATE INDEX IF NOT EXISTS idx_tenant_pricing_demo ON tenant_pricing_levels(is_demo)",
            "CREATE INDEX IF NOT EXISTS idx_boq_history_demo ON boq_generation_history(is_demo)",
            "CREATE INDEX IF NOT EXISTS idx_tender_analyses_demo ON tender_analyses(is_demo)",
        ]
        
        for idx in indexes:
            try:
                cursor.execute(idx)
                logger.info(f"  ✅ Created index: {idx.split('ON')[1].strip().split('(')[0]}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not create index: {e}")
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v014")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Drop new tables
                tables = ['demo_data_generation_log', 'company_onboarding_status']
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"  ✅ Dropped table: {table}")
                
                # Note: Can't easily drop columns in SQLite
                logger.info("  ℹ️ Columns will remain (SQLite doesn't support DROP COLUMN)")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False