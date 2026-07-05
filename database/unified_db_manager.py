# database/unified_db_manager.py

import os
import logging
from typing import Optional, Dict, List, Any
import streamlit as st

from database.connection import get_supabase_client, get_connection, get_db_type, is_supabase
from database.supabase_sql_wrapper import SupabaseSQLWrapper
from database.crud_operations import DatabaseCRUD

logger = logging.getLogger(__name__)


class UnifiedDatabaseManager:
    """Unified Database Manager - delegates to crud_operations.py"""

    def __init__(self):
        self.db_type = get_db_type()
        self._use_supabase = is_supabase()
        
        # Initialize CRUD immediately
        self._crud = DatabaseCRUD()

        # Supabase client
        self.supabase_client = None
        if self._use_supabase:
            self.supabase_client = get_supabase_client()
            logger.info("✅ Supabase client attached")

        if not self._use_supabase:
            self._create_tables_if_needed()

    @property
    def crud(self):
        return self._crud

    def _create_tables_if_needed(self):
        """SQLite only"""
        try:
            from database.schema import DatabaseSchema
            schema = DatabaseSchema("data/tender_system.db")
            schema.create_all_tables()
            schema.insert_default_data()
        except Exception as e:
            logger.warning(f"Table creation warning: {e}")

    # ====================== Supabase Table Access ======================
    def table(self, table_name: str):
        if not self.supabase_client:
            raise AttributeError("Supabase client not available")
        return self.supabase_client.table(table_name)

    # ====================== Connection Helpers ======================
    def get_connection(self):
        return get_connection()

    def get_cursor(self, conn=None):
        if self._use_supabase:
            return SupabaseSQLWrapper(get_connection())
        conn = conn or self.get_connection()
        return conn.cursor()

    # ====================== Delegation Methods ======================
    
    # These methods delegate to crud - add more as needed
    def create_google_user(self, user_data):
        return self.crud.create_google_user(user_data)
    
    def get_user_by_email(self, email):
        return self.crud.get_user_by_email(email)
    
    def get_user_by_id(self, user_id):
        return self.crud.get_user_by_id(user_id)
    
    def get_all_users(self, company_id=None, role=None):
        """Get all users as dictionaries"""
        return self.crud.get_all_users(company_id=company_id, role=role)

    
    def get_db_type(self):
        return self.db_type
    
    def get_supabase_client(self):
        return self.supabase_client

    # ====================== Fallback Delegation ======================
    def __getattr__(self, name: str):
        """
        Delegate unknown methods to CRUD layer.
        Only delegates callable methods.
        """
        # Skip our own methods
        if name in {'crud', 'get_connection', 'get_supabase_client', 
                   'get_db_type', 'table'}:
            return getattr(self, name)
        
        # Delegate to crud if it has the method
        if hasattr(self.crud, name):
            attr = getattr(self.crud, name)
            if callable(attr):
                return attr
            return attr
        
        # Method not found
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


@st.cache_resource(show_spinner=False)
def get_db_manager() -> UnifiedDatabaseManager:
    return UnifiedDatabaseManager()


def get_db():
    return get_db_manager()


__all__ = ['UnifiedDatabaseManager', 'get_db_manager', 'get_db']