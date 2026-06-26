# migrations/v015_archive_framework.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV015:
    """Migration v015: Add archive framework tables and columns"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v015: Archive Framework")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Create archive records table
                self._create_archive_records(cursor)
                
                # 2. Create archive metadata table
                self._create_archive_metadata(cursor)
                
                # 3. Add archive columns to existing tables
                self._add_archive_columns(cursor)
                
                # 4. Create indexes
                self._create_indexes(cursor)
                
                conn.commit()
                logger.info("✅ Migration v015 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v015 failed: {e}")
            return False
    
    def _create_archive_records(self, cursor):
        """Create table to track archived records"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                company_id INTEGER,
                archive_reason TEXT,
                archived_by INTEGER,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_snapshot TEXT,  -- JSON snapshot of the data before archive
                restored_by INTEGER,
                restored_at TIMESTAMP,
                is_restored BOOLEAN DEFAULT 0,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
                FOREIGN KEY (archived_by) REFERENCES users(id),
                FOREIGN KEY (restored_by) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: archive_records")
    
    def _create_archive_metadata(self, cursor):
        """Create table to store archive metadata"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                archive_batch_id TEXT NOT NULL,
                company_id INTEGER,
                operation_type TEXT NOT NULL,  -- 'DEMO_RESET', 'PRODUCTION_SWITCH', 'FULL_RESET'
                description TEXT,
                total_records_archived INTEGER DEFAULT 0,
                total_records_deleted INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed',
                initiated_by INTEGER,
                initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
                FOREIGN KEY (initiated_by) REFERENCES users(id)
            )
        """)
        logger.info("  ✅ Created table: archive_metadata")
    
    def _add_archive_columns(self, cursor):
        """Add archive columns to existing tables"""
        
        tables = [
            'tenant_rate_books',
            'tenant_rate_versions',
            'tenant_rate_items',
            'tenant_pricing_levels',
            'boq_generation_history',
            'boq_items',
            'tender_analyses',
            'company_tenders',
            'saved_scenarios'
        ]
        
        for table in tables:
            columns = [
                ('is_archived', 'BOOLEAN DEFAULT 0'),
                ('archived_at', 'TIMESTAMP'),
                ('archived_by', 'INTEGER'),
                ('archive_reason', 'TEXT')
            ]
            
            for column, column_type in columns:
                if not self.db.column_exists(table, column):
                    try:
                        sql = f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
                        cursor.execute(sql)
                        logger.info(f"  ✅ Added column: {table}.{column}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Could not add {table}.{column}: {e}")
                else:
                    logger.info(f"  ℹ️ Column already exists: {table}.{column}")
    
    def _create_indexes(self, cursor):
        """Create indexes for performance"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_archive_source ON archive_records(source_table, source_id)",
            "CREATE INDEX IF NOT EXISTS idx_archive_company ON archive_records(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON archive_records(archived_at)",
            "CREATE INDEX IF NOT EXISTS idx_archive_batch ON archive_metadata(archive_batch_id, company_id)",
            "CREATE INDEX IF NOT EXISTS idx_tenant_books_archived ON tenant_rate_books(is_archived)",
            "CREATE INDEX IF NOT EXISTS idx_boq_history_archived ON boq_generation_history(is_archived)",
            "CREATE INDEX IF NOT EXISTS idx_tender_analyses_archived ON tender_analyses(is_archived)",
        ]
        
        for idx in indexes:
            try:
                cursor.execute(idx)
                logger.info(f"  ✅ Created index: {idx.split('ON')[1].strip().split('(')[0]}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not create index: {e}")
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v015")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                tables = ['archive_metadata', 'archive_records']
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"  ✅ Dropped table: {table}")
                
                logger.info("  ℹ️ Archive columns will remain (SQLite doesn't support DROP COLUMN)")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False