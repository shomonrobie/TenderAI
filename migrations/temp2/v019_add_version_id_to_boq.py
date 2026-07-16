# migrations/v019_add_version_id_to_boq.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV019:
    """Migration v019: Add rate_book_id and version_id columns to boq_generation_history"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v019: Add rate_book_id and version_id to boq_generation_history")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check existing columns
                cursor.execute("PRAGMA table_info(boq_generation_history)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Add rate_book_id if not exists
                if 'rate_book_id' not in columns:
                    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN rate_book_id INTEGER")
                    logger.info("  ✅ Added column: rate_book_id")
                else:
                    logger.info("  ℹ️ Column rate_book_id already exists")
                
                # Add version_id if not exists
                if 'version_id' not in columns:
                    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN version_id INTEGER")
                    logger.info("  ✅ Added column: version_id")
                else:
                    logger.info("  ℹ️ Column version_id already exists")
                
                # ✅ Add foreign key constraints if using SQLite (they won't be enforced automatically)
                # For SQLite, we need to recreate the table to add FKs, or just rely on app-level integrity
                # We'll add indexes for performance instead
                
                # Add indexes for the new columns
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_history_rate_book ON boq_generation_history(rate_book_id)")
                logger.info("  ✅ Created index: idx_boq_history_rate_book")
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_history_version ON boq_generation_history(version_id)")
                logger.info("  ✅ Created index: idx_boq_history_version")
                
                conn.commit()
                logger.info("✅ Migration v019 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v019 failed: {e}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v019")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Drop indexes
                cursor.execute("DROP INDEX IF EXISTS idx_boq_history_rate_book")
                cursor.execute("DROP INDEX IF EXISTS idx_boq_history_version")
                logger.info("  ✅ Dropped indexes")
                
                # Note: SQLite doesn't support DROP COLUMN directly
                # We would need to recreate the table without these columns
                # For simplicity, we'll just log a warning
                logger.info("  ℹ️ Columns remain (SQLite doesn't support DROP COLUMN)")
                logger.info("  ℹ️ To rollback fully, you would need to:")
                logger.info("  ℹ️ 1. Create a new table without the columns")
                logger.info("  ℹ️ 2. Copy data from old table")
                logger.info("  ℹ️ 3. Drop old table and rename new table")
                
                conn.commit()
                logger.info("✅ Rollback completed (partial)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False