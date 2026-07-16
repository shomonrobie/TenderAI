# migrations/v017_add_step_data_column.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV017:
    """Migration v017: Add step_data column to company_onboarding_status"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v017: Add step_data column")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if column exists
                cursor.execute("PRAGMA table_info(company_onboarding_status)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'step_data' not in columns:
                    cursor.execute("ALTER TABLE company_onboarding_status ADD COLUMN step_data TEXT")
                    logger.info("  ✅ Added column: step_data")
                else:
                    logger.info("  ℹ️ Column step_data already exists")
                
                conn.commit()
                logger.info("✅ Migration v017 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v017 failed: {e}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v017")
        logger.info("  ℹ️ Columns will remain (SQLite doesn't support DROP COLUMN)")
        return True