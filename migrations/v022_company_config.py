# migrations/v022_company_config.py

import logging
import json
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV022:
    """Migration v022: Add company_config table for company-specific settings"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v022: Add company_config table")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create company_config table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER NOT NULL,
                        config_key TEXT NOT NULL,
                        config_value TEXT NOT NULL,
                        config_type TEXT DEFAULT 'string',
                        description TEXT,
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_by INTEGER,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                        FOREIGN KEY (created_by) REFERENCES users(id),
                        FOREIGN KEY (updated_by) REFERENCES users(id),
                        UNIQUE(company_id, config_key)
                    )
                """)
                logger.info("  ✅ Created table: company_config")
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_company_config_company 
                    ON company_config(company_id)
                """)
                logger.info("  ✅ Created index: idx_company_config_company")
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_company_config_key 
                    ON company_config(config_key)
                """)
                logger.info("  ✅ Created index: idx_company_config_key")
                
                # Insert default company configs for existing companies
                # (Optional - you can skip this and let the system use defaults)
                
                conn.commit()
                logger.info("✅ Migration v022 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v022 failed: {e}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v022")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DROP TABLE IF EXISTS company_config")
                logger.info("  ✅ Dropped table: company_config")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False