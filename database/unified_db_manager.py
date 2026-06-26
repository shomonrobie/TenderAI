# database/unified_db_manager.py - FIXED to work like old version

import sqlite3
import os
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class UnifiedDatabaseManager:
    """Single unified database manager - works like old db_manager.py"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize CRUD operations (without the context manager)
        from database.crud_operations import DatabaseCRUD
        self.crud = DatabaseCRUD(db_path)
        
        # Create tables if needed
        self._create_tables_if_needed()
        
        logger.info(f"UnifiedDatabaseManager initialized: {db_path}")
    
    def _create_tables_if_needed(self):
        """Create tables if they don't exist"""
        try:
            from database.schema import DatabaseSchema
            schema = DatabaseSchema(self.db_path)
            schema.create_all_tables()
            schema.insert_default_data()
        except Exception as e:
            logger.warning(f"Table creation error: {e}")
    
    # ========== THE KEY FIX - Return raw connection like old version ==========
    def get_connection(self):
        """
        Returns raw database connection (works exactly like old db_manager.py)
        Usage: conn = db.get_connection()
               cursor = conn.cursor()
               # ... work ...
               conn.close()
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    # ==========================================================================
    
    # Delegate all other methods to crud
    def __getattr__(self, name):
        """Delegate method calls to crud operations"""
        return getattr(self.crud, name)
    
    def __dir__(self):
        return list(set(super().__dir__() + dir(self.crud)))


# Singleton instance
db = UnifiedDatabaseManager()

__all__ = ['UnifiedDatabaseManager', 'db']