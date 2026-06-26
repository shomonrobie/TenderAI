# migrations/v023_add_quick_boq.py - COMPLETE FIXED VERSION

import logging
import sqlite3
import os

logger = logging.getLogger(__name__)

class MigrationV023:
    """Migration v023: Add is_quick_boq column to boq_generation_history"""
    
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
        logger.info("🚀 Running migration v023: Add is_quick_boq column")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ✅ FIX: Use proper PRAGMA syntax and handle result correctly
            cursor.execute("PRAGMA table_info(boq_generation_history)")
            rows = cursor.fetchall()
            
            # Extract column names from PRAGMA result
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            columns = [row[1] for row in rows if row]  # row[1] is the column name
            
            logger.info(f"📋 Existing columns: {columns}")
            
            if 'is_quick_boq' not in columns:
                cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN is_quick_boq BOOLEAN DEFAULT 0")
                logger.info("  ✅ Added column: is_quick_boq")
            else:
                logger.info("  ℹ️ Column is_quick_boq already exists")
            
            # Verify column was added
            cursor.execute("PRAGMA table_info(boq_generation_history)")
            rows = cursor.fetchall()
            columns = [row[1] for row in rows if row]
            
            if 'is_quick_boq' in columns:
                logger.info("  ✅ Verified column exists")
            else:
                logger.warning("  ⚠️ Column not found after ALTER")
            
            # Add index for quick BOQs
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_quick ON boq_generation_history(is_quick_boq)")
            logger.info("  ✅ Created index: idx_boq_quick")
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Migration v023 completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration v023 failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v023")
        logger.info("  ℹ️ Columns will remain (SQLite doesn't support DROP COLUMN)")
        return True