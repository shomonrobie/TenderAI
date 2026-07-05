# database/connection.py

import os
import logging
from typing import Optional
import streamlit as st
from contextlib import contextmanager
import sqlite3

logger = logging.getLogger(__name__)

# Global variables for the connection
_db_type: str = "supabase"  # default
_supabase_client = None
_sqlite_connection = None  # Cache SQLite connection


def init_db_connection(db_type: str = "supabase"):
    """
    Initialize the database connection type (call once at app startup)
    
    Args:
        db_type: 'supabase' or 'sqlite'
    """
    global _db_type
    _db_type = db_type.lower()
    logger.info(f"✅ Database connection initialized with type: {_db_type}")


@st.cache_resource(show_spinner=False)
def get_supabase_client():
    """
    Return a cached Supabase client - created only once per Streamlit process.
    Uses @st.cache_resource for optimal performance.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    try:
        from supabase import create_client
        
        # Try multiple sources for credentials
        url = None
        key = None
        
        # 1. Try config.database
        try:
            from config.database import DB_CONFIG
            url = DB_CONFIG.get("url")
            key = DB_CONFIG.get("key")
        except ImportError:
            pass
        
        # 2. Try Streamlit secrets (connections format)
        if not url or not key:
            try:
                if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
                    supabase_config = st.secrets["connections"]["supabase"]
                    url = supabase_config.get("SUPABASE_URL")
                    key = supabase_config.get("SUPABASE_KEY")
            except:
                pass
        
        # 3. Try Streamlit secrets (flat format)
        if not url or not key:
            try:
                url = st.secrets.get("SUPABASE_URL")
                key = st.secrets.get("SUPABASE_KEY")
            except:
                pass
        
        # 4. Try environment variables
        if not url or not key:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("Supabase URL and Key not found in config, secrets, or environment")

        _supabase_client = create_client(url, key)
        logger.info("✅ Supabase client successfully created and cached")
        return _supabase_client

    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {e}")
        raise


def _create_sqlite_connection():
    """Create a new SQLite connection"""
    db_path = "data/tender_system.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(
        db_path, 
        timeout=30,
        check_same_thread=False,  # Allow use across threads
        isolation_level=None  # Auto-commit mode helps in some cases
    )
    conn.row_factory = sqlite3.Row
    return conn



@st.cache_resource(show_spinner=False)
def get_sqlite_connection():
    """Always returns a valid open connection"""
    global _sqlite_connection
    
    if _sqlite_connection is None or not _is_connection_open(_sqlite_connection):
        _sqlite_connection = _create_sqlite_connection()
        logger.info("✅ SQLite connection (re)created")
    
    return _sqlite_connection

def _is_connection_open(conn) -> bool:
    if conn is None:
        return False
    try:
        conn.execute("SELECT 1")
        return True
    except:
        return False
    
def get_connection():
    """
    Get database connection (database-agnostic).
    For Supabase: returns the client directly
    For SQLite: returns the SQLite connection
    """
    print(f"🔍 get_connection() called, _db_type={_db_type}")
    
    if _db_type == "supabase":
        client = get_supabase_client()
        print(f"🔍 Returning Supabase client: {client is not None}")
        return client
    else:
        conn = get_sqlite_connection()
        print(f"🔍 Returning SQLite connection: {conn is not None}")
        return conn



@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Auto-reopens if connection is closed.
    
    Usage:
        with get_db_connection() as conn:
            # Use conn
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        # For SQLite, we DON'T close the connection - keep it cached
        # The connection will be checked and reopened if needed next time
        pass


def get_cursor(conn=None):
    """
    Get a cursor from a connection.
    Auto-reopens if connection is closed.
    For Supabase, returns a wrapped cursor.
    For SQLite, returns a regular cursor.
    """
    if _db_type == "supabase":
        from database.supabase_sql_wrapper import SupabaseSQLWrapper
        return SupabaseSQLWrapper(get_connection())
    else:
        if conn is None:
            conn = get_connection()
        return conn.cursor()


def get_db_type() -> str:
    """Get current database type"""
    return _db_type


def is_supabase() -> bool:
    """Check if using Supabase"""
    return _db_type == "supabase"


def is_sqlite() -> bool:
    """Check if using SQLite"""
    return _db_type == "sqlite"

class SupabaseContextWrapper:
    """Simple wrapper to support context manager pattern for Supabase"""
    
    def __init__(self, client):
        self.client = client
        self._wrapper = None
        print(f"🔍 SupabaseContextWrapper created")
    
    def __enter__(self):
        print(f"🔍 SupabaseContextWrapper.__enter__ called")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"🔍 SupabaseContextWrapper.__exit__ called")
        pass
    
    def _get_wrapper(self):
        """Get or create the SQL wrapper"""
        if self._wrapper is None:
            from database.supabase_sql_wrapper import SupabaseSQLWrapper
            self._wrapper = SupabaseSQLWrapper(self.client)
        return self._wrapper
    
    # ✅ Only these explicit methods are needed
    def execute(self, sql: str, params: tuple = None):
        """Execute SQL"""
        return self._get_wrapper().execute(sql, params)
    
    def fetchone(self):
        """Fetch one row"""
        return self._get_wrapper().fetchone()
    
    def fetchall(self):
        """Fetch all rows"""
        return self._get_wrapper().fetchall()
    
    def commit(self):
        """Commit (no-op for Supabase)"""
        return self
    
    def rollback(self):
        """Rollback (no-op for Supabase)"""
        return self
    
    def close(self):
        """Close (no-op for Supabase)"""
        return self

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# class SupabaseContextWrapper:
#     """Backward compatibility wrapper for old code"""
#     def __init__(self, client=None):
#         self.client = client or get_supabase_client()
#         self._cursor = None
    
#     def __enter__(self):
#         return self
    
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         pass
    
#     def cursor(self):
#         from database.supabase_sql_wrapper import SupabaseSQLWrapper
#         if self._cursor is None:
#             self._cursor = SupabaseSQLWrapper(get_connection())
#         return self._cursor
    
#     def execute(self, sql: str, params: tuple = None):
#         cursor = self.cursor()
#         return cursor.execute(sql, params)
    
#     def fetchone(self):
#         return self.cursor().fetchone()
    
#     def fetchall(self):
#         return self.cursor().fetchall()
    
    
#     # ✅ FIX: Only delegate if method exists on wrapper or client
#     # def __getattr__(self, name):
#     #     """Delegate any other calls to the wrapper or client"""
#     #     print(f"🔍 Connection SupabaseContextWrapper.__getattr__: {name}")
        
#     #     # Try the wrapper first
#     #     wrapper = self._get_wrapper()
#     #     if hasattr(wrapper, name):
#     #         attr = getattr(wrapper, name)
#     #         if callable(attr):
#     #             print(f"✅ Delegating {name} to wrapper")
#     #             return attr
#     #         return attr
        
#     #     # Try the client
#     #     if hasattr(self.client, name):
#     #         attr = getattr(self.client, name)
#     #         if callable(attr):
#     #             print(f"✅ Delegating {name} to client")
#     #             return attr
#     #         return attr
        
#     #     # Not found
#     #     raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

# # For backward compatibility
# db_connection = get_connection()

# # Update __all__
# __all__ = [
#     'init_db_connection',
#     'get_supabase_client',
#     'get_sqlite_connection',
#     'get_connection',
#     'get_db_connection',
#     'get_cursor',
#     'get_db_type',
#     'is_supabase',
#     'is_sqlite',
#     'db_connection',
#     'SupabaseContextWrapper',
# ]