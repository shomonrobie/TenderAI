# migrations/v018_add_custom_source_column.py - FIXED

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV018:
    """Migration v018: Add custom_source column for better tracking"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v018: Add custom_source column")
        
        try:
            # ✅ Get connection directly
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if columns exist
            cursor.execute("PRAGMA table_info(tenant_rate_books)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add custom_source if not exists
            if 'custom_source' not in columns:
                try:
                    cursor.execute("ALTER TABLE tenant_rate_books ADD COLUMN custom_source TEXT")
                    logger.info("  ✅ Added column: custom_source")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not add custom_source: {e}")
            else:
                logger.info("  ℹ️ Column custom_source already exists")
            
            # Add version_notes if not exists
            if 'version_notes' not in columns:
                try:
                    cursor.execute("ALTER TABLE tenant_rate_books ADD COLUMN version_notes TEXT")
                    logger.info("  ✅ Added column: version_notes")
                except Exception as e:
                    logger.warning(f"  ⚠️ Could not add version_notes: {e}")
            else:
                logger.info("  ℹ️ Column version_notes already exists")
            
            # ✅ Commit the changes
            conn.commit()
            conn.close()
            
            logger.info("✅ Migration v018 completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration v018 failed: {e}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v018")
        logger.info("  ℹ️ Columns will remain (SQLite doesn't support DROP COLUMN)")
        return True