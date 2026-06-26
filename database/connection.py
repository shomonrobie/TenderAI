# database/connection.py
"""Database-agnostic connection manager"""

import os
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class RowFactory:
    """Wrapper to make any database row behave like a dictionary"""
    
    @staticmethod
    def sqlite_row_factory(cursor, row):
        """Convert SQLite row to dict"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    
    @staticmethod
    def dict_row(cursor, row):
        """Generic dict row factory"""
        return dict(zip([col[0] for col in cursor.description], row))


class DatabaseConnection:
    """Manages database connections for multiple database types"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._db_type = None  # Use private variable, not property
            self._connect_func = None
            self._init_connection()
            self._initialized = True
    
    def _init_connection(self):
        """Initialize connection based on database type"""
        from config.database import DB_CONFIG
        
        self._db_type = DB_CONFIG['type']  # Use private variable
        
        if self._db_type == 'sqlite':
            self._init_sqlite()
        elif self._db_type == 'postgresql':
            self._init_postgresql()
        elif self._db_type == 'mysql':
            self._init_mysql()
        elif self._db_type == 'cockroachdb':
            self._init_cockroachdb()
        else:
            raise ValueError(f"Unsupported database type: {self._db_type}")
    
    def _init_sqlite(self):
        """Initialize SQLite connection"""
        import sqlite3
        from config.database import DB_CONFIG
        
        db_path = DB_CONFIG.get('path', 'data/tender_system.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        def connect():
            conn = sqlite3.connect(db_path)
            # Use custom row factory that returns dicts
            conn.row_factory = RowFactory.sqlite_row_factory
            return conn
        
        self._connect_func = connect
    
    def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        try:
            import psycopg2
            import psycopg2.extras
            
            from config.database import DB_CONFIG
            
            def connect():
                conn = psycopg2.connect(
                    host=DB_CONFIG.get('host', 'localhost'),
                    port=DB_CONFIG.get('port', 5432),
                    database=DB_CONFIG.get('database', 'tenderai'),
                    user=DB_CONFIG.get('user', 'postgres'),
                    password=DB_CONFIG.get('password', '')
                )
                # Use RealDictCursor for dictionary-like rows
                return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor).connection
            self._connect_func = connect
        except ImportError:
            raise ImportError("psycopg2 required for PostgreSQL. pip install psycopg2-binary")
    
    def _init_mysql(self):
        """Initialize MySQL/MariaDB connection"""
        try:
            import pymysql
            from pymysql.cursors import DictCursor
            
            from config.database import DB_CONFIG
            
            def connect():
                return pymysql.connect(
                    host=DB_CONFIG.get('host', 'localhost'),
                    port=DB_CONFIG.get('port', 3306),
                    database=DB_CONFIG.get('database', 'tenderai'),
                    user=DB_CONFIG.get('user', 'root'),
                    password=DB_CONFIG.get('password', ''),
                    cursorclass=DictCursor  # Returns dict rows
                )
            self._connect_func = connect
        except ImportError:
            raise ImportError("pymysql required for MySQL. pip install pymysql")
    
    def _init_cockroachdb(self):
        """Initialize CockroachDB connection"""
        try:
            import psycopg2
            import psycopg2.extras
            
            from config.database import DB_CONFIG
            
            def connect():
                conn = psycopg2.connect(
                    host=DB_CONFIG.get('host', 'localhost'),
                    port=DB_CONFIG.get('port', 26257),
                    database=DB_CONFIG.get('database', 'tenderai'),
                    user=DB_CONFIG.get('user', 'root'),
                    password=DB_CONFIG.get('password', '')
                )
                return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor).connection
            self._connect_func = connect
        except ImportError:
            raise ImportError("psycopg2 required for CockroachDB")
    
    def get_connection(self):
        """Returns database connection (raw connection, not context manager)"""
        return self._connect_func()
    
    def get_cursor(self, conn):
        """Get cursor (already configured for dict rows)"""
        return conn.cursor()
    
    @property
    def db_type(self):
        """Get current database type"""
        return self._db_type


# Global instance
db_connection = DatabaseConnection()