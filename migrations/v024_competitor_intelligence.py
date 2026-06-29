"""
Migration v024: Add competitor intelligence features
- Adds 'details' column to competitor_master
- Adds indexes for performance optimization
"""

from database.crud_operations import DatabaseCRUD
import logging

logger = logging.getLogger(__name__)

class MigrationV024:
    """Migration to add competitor intelligence features"""
    
    def __init__(self, db: DatabaseCRUD):
        self.db = db
    
    def up(self) -> bool:
        """Apply migration"""
        try:
            logger.info("🔄 Running v024 migration: Adding competitor intelligence features...")
            
            # 1. Add 'details' column to competitor_master
            if not self.db.column_exists('competitor_master', 'details'):
                with self.db.get_connection() as conn:
                    cursor = self.db.db_conn.get_cursor(conn)
                    cursor.execute("""
                        ALTER TABLE competitor_master 
                        ADD COLUMN details TEXT
                    """)
                    logger.info("✅ Added 'details' column to competitor_master")
            else:
                logger.info("ℹ️ 'details' column already exists")
            
            # 2. Add indexes for performance
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                
                # Index for competitor bid history lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_competitor_bid_history_competitor 
                    ON competitor_bid_history(competitor_name, company_id)
                """)
                logger.info("✅ Added index idx_competitor_bid_history_competitor")
                
                # Index for tender lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_competitor_bid_history_tender 
                    ON competitor_bid_history(tender_id)
                """)
                logger.info("✅ Added index idx_competitor_bid_history_tender")
                
                # Index for competitor master
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_competitor_master_company 
                    ON competitor_master(company_id)
                """)
                logger.info("✅ Added index idx_competitor_master_company")
            
            logger.info("✅ v024 migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ v024 migration failed: {str(e)}")
            return False
    
    def down(self) -> bool:
        """Rollback migration"""
        try:
            logger.info("🔄 Rolling back v024 migration...")
            
            # Remove indexes (SQLite doesn't support DROP COLUMN easily)
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                cursor.execute("DROP INDEX IF EXISTS idx_competitor_bid_history_competitor")
                cursor.execute("DROP INDEX IF EXISTS idx_competitor_bid_history_tender")
                cursor.execute("DROP INDEX IF EXISTS idx_competitor_master_company")
                logger.info("✅ Removed indexes")
            
            logger.info("✅ v024 rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ v024 rollback failed: {str(e)}")
            return False