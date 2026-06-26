# migrations/v020_rename_cost_levels.py

import logging
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)

class MigrationV020:
    """Migration v020: Rename pricing levels to cost levels"""
    
    def __init__(self, db_crud: DatabaseCRUD = None):
        self.db = db_crud or DatabaseCRUD()
    
    def up(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Running migration v020: Rename cost levels")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update existing records to new naming
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET pricing_level = 'AGGRESSIVE' 
                    WHERE pricing_level = 'ECONOMY'
                """)
                logger.info("  ✅ Renamed ECONOMY → AGGRESSIVE")
                
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET pricing_level = 'COMPETITIVE' 
                    WHERE pricing_level = 'MARKET'
                """)
                logger.info("  ✅ Renamed MARKET → COMPETITIVE")
                
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET pricing_level = 'STANDARD' 
                    WHERE pricing_level = 'PREMIUM'
                """)
                logger.info("  ✅ Renamed PREMIUM → STANDARD")
                
                conn.commit()
                logger.info("✅ Migration v020 completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration v020 failed: {e}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        logger.info("⚠️ Rolling back migration v020")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Revert to old names
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET pricing_level = 'ECONOMY' 
                    WHERE pricing_level = 'AGGRESSIVE'
                """)
                logger.info("  ✅ Reverted AGGRESSIVE → ECONOMY")
                
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET pricing_level = 'MARKET' 
                    WHERE pricing_level = 'COMPETITIVE'
                """)
                logger.info("  ✅ Reverted COMPETITIVE → MARKET")
                
                cursor.execute("""
                    UPDATE tenant_pricing_levels 
                    SET pricing_level = 'PREMIUM' 
                    WHERE pricing_level = 'STANDARD'
                """)
                logger.info("  ✅ Reverted STANDARD → PREMIUM")
                
                conn.commit()
                logger.info("✅ Rollback completed successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False