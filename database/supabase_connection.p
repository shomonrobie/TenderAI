# database/supabase_connection.py

import streamlit as st
from st_supabase_connection import SupabaseConnection
import json
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class SupabaseDBConnection:
    """
    Wrapper class to make Supabase work with your existing crud_operations.py
    This mimics the SQLite/PostgreSQL connection interface
    """
    
    def __init__(self):
        self.db_type = 'postgresql'  # Supabase is PostgreSQL
        self._conn = None
        self._cursor_class = self._SupabaseCursor
        
    class _SupabaseCursor:
        """Mimics database cursor for Supabase"""
        def __init__(self, conn, table_name=None):
            self.conn = conn
            self.table_name = table_name
            self._result = None
            self._rowcount = 0
            self._lastrowid = None
        
        def execute(self, sql: str, params: tuple = None):
            """Execute SQL query - converts SQLite syntax to Supabase"""
            # For SELECT queries, use supabase table methods
            # For INSERT/UPDATE/DELETE, use supabase table methods
            
            # Simple SQL parser for basic operations
            sql_upper = sql.strip().upper()
            
            if sql_upper.startswith('SELECT'):
                return self._handle_select(sql, params)
            elif sql_upper.startswith('INSERT'):
                return self._handle_insert(sql, params)
            elif sql_upper.startswith('UPDATE'):
                return self._handle_update(sql, params)
            elif sql_upper.startswith('DELETE'):
                return self._handle_delete(sql, params)
            elif sql_upper.startswith('PRAGMA'):
                # PRAGMA statements are SQLite-specific, return mock data
                self._result = []
                return self
            else:
                # For other queries, try to execute as is
                try:
                    result = self.conn.table(self._get_table_name(sql)).execute()
                    self._result = result.data if result else []
                    return self
                except Exception as e:
                    logger.error(f"Error executing SQL: {sql}, Error: {e}")
                    self._result = []
                    return self
        
        def _handle_select(self, sql: str, params: tuple = None):
            """Parse SELECT query and convert to Supabase API call"""
            try:
                # Check if it's a SQLite system table query
                sql_lower = sql.lower()
                if 'sqlite_master' in sql_lower or 'pragma' in sql_lower:
                    # Return empty result for SQLite system queries
                    self._result = []
                    self._rowcount = 0
                    return self
                
                # Extract table name
                from_idx = sql_lower.find('from')
                if from_idx == -1:
                    self._result = []
                    self._rowcount = 0
                    return self
                
                after_from = sql[from_idx + 4:].strip()
                table_name = after_from.split()[0].strip()
                
                # Build query
                query = self.client.table(table_name).select('*')
                
                # Parse WHERE clause
                if 'where' in sql_lower:
                    where_clause = sql_lower.split('where')[1].split('order')[0].split('limit')[0].strip()
                    if '=' in where_clause:
                        parts = where_clause.split('=', 1)
                        if len(parts) == 2:
                            col = parts[0].strip()
                            val = parts[1].strip()
                            if val == '?' and params:
                                query = query.eq(col, params[0])
                            elif val.startswith("'") and val.endswith("'"):
                                query = query.eq(col, val[1:-1])
                            else:
                                try:
                                    query = query.eq(col, int(val))
                                except:
                                    query = query.eq(col, val)
                
                # Execute
                result = query.execute()
                self._result = result.data if result else []
                self._rowcount = len(self._result)
                
            except Exception as e:
                print(f"⚠️ Supabase query parse error: {e}")
                self._result = []
                self._rowcount = 0
            
            return self

        
        def _handle_insert(self, sql: str, params: tuple = None):
            """Handle INSERT queries"""
            table_name = self._extract_table_name(sql)
            if not table_name:
                self._result = []
                return self
            
            # Extract columns and values (simplified)
            values_start = sql.find('VALUES')
            if values_start == -1:
                self._result = []
                return self
            
            # Get column names
            columns_part = sql[sql.find('(')+1:sql.find(')')]
            columns = [c.strip() for c in columns_part.split(',') if c.strip()]
            
            # Get values
            values_part = sql[sql.find('VALUES')+6:].strip().strip('()')
            # Remove any trailing semicolon
            values_part = values_part.rstrip(';')
            
            # Parse values - handle both ? placeholders and actual values
            if '?' in values_part and params:
                values = params
            else:
                # Parse literal values (simplified)
                values = []
                current = ''
                in_string = False
                for char in values_part:
                    if char == "'" and not in_string:
                        in_string = True
                        current += char
                    elif char == "'" and in_string:
                        in_string = False
                        current += char
                        values.append(current)
                        current = ''
                    elif char == ',' and not in_string:
                        if current.strip():
                            values.append(current.strip())
                        current = ''
                    else:
                        current += char
                if current.strip():
                    values.append(current.strip())
            
            # Build data dict
            data = {}
            for i, col in enumerate(columns):
                if i < len(values):
                    val = values[i]
                    # Remove quotes if it's a string literal
                    if isinstance(val, str) and val.startswith("'") and val.endswith("'"):
                        val = val[1:-1]
                    data[col] = val
            
            # Insert
            result = self.conn.table(table_name).insert(data).execute()
            self._result = result.data if result else []
            self._rowcount = len(self._result)
            if result.data:
                # Get the first column name for lastrowid (usually 'id')
                first_col = list(result.data[0].keys())[0] if result.data else None
                self._lastrowid = result.data[0].get(first_col) if first_col else None
            else:
                self._lastrowid = None
            return self
        
        def _handle_update(self, sql: str, params: tuple = None):
            """Handle UPDATE queries"""
            table_name = self._extract_table_name(sql)
            if not table_name:
                self._result = []
                return self
            
            # Extract SET clause (simplified)
            set_start = sql.upper().find('SET') + 3
            where_start = sql.upper().find('WHERE')
            set_clause = sql[set_start:where_start if where_start != -1 else None].strip()
            
            # Parse SET clause
            data = {}
            # Handle multiple SET statements
            for part in set_clause.split(','):
                if '=' in part:
                    col, val = part.split('=', 1)
                    col = col.strip()
                    val = val.strip()
                    if val.startswith('?') and params:
                        data[col] = params[0]
                        params = params[1:] if params else []
                    elif val.startswith("'") and val.endswith("'"):
                        data[col] = val[1:-1]
                    else:
                        try:
                            data[col] = int(val)
                        except:
                            try:
                                data[col] = float(val)
                            except:
                                data[col] = val
            
            # Handle WHERE clause
            if where_start != -1:
                where_clause = sql[where_start+5:].strip().split('ORDER')[0].split('LIMIT')[0].strip()
                # Parse WHERE (simplified - only supports = with ?)
                if '=' in where_clause:
                    col, val = where_clause.split('=', 1)
                    col = col.strip()
                    val = val.strip()
                    if val.startswith('?') and params:
                        condition_col = col
                        condition_val = params[0]
                    else:
                        condition_col = col
                        condition_val = val.strip("'")
                    
                    # Update with filter
                    result = self.conn.table(table_name).update(data).eq(condition_col, condition_val).execute()
                    self._result = result.data if result else []
                    self._rowcount = len(self._result)
                    return self
            
            # No WHERE clause - update all rows (use with caution)
            result = self.conn.table(table_name).update(data).execute()
            self._result = result.data if result else []
            self._rowcount = len(self._result)
            return self
        
        def _handle_delete(self, sql: str, params: tuple = None):
            """Handle DELETE queries"""
            table_name = self._extract_table_name(sql)
            if not table_name:
                self._result = []
                return self
            
            # Parse WHERE clause (simplified)
            if 'WHERE' in sql.upper():
                where_clause = sql.split('WHERE')[1].strip().split('ORDER')[0].split('LIMIT')[0].strip()
                if '=' in where_clause:
                    col, val = where_clause.split('=', 1)
                    col = col.strip()
                    val = val.strip()
                    if val.startswith('?') and params:
                        result = self.conn.table(table_name).delete().eq(col, params[0]).execute()
                    else:
                        result = self.conn.table(table_name).delete().eq(col, val.strip("'")).execute()
                    self._result = result.data if result else []
                    self._rowcount = len(self._result)
                    return self
            
            # No WHERE - delete all rows (use with extreme caution)
            result = self.conn.table(table_name).delete().execute()
            self._result = result.data if result else []
            self._rowcount = len(self._result)
            return self
        
        def _extract_table_name(self, sql: str) -> str:
            """Extract table name from SQL"""
            sql_upper = sql.upper()
            for keyword in ['FROM', 'INSERT INTO', 'UPDATE', 'DELETE FROM']:
                if keyword in sql_upper:
                    idx = sql_upper.find(keyword) + len(keyword)
                    # Find the table name (up to space, (, or newline)
                    remaining = sql[idx:].strip()
                    table = remaining.split()[0].strip()
                    # Remove any trailing punctuation
                    table = table.rstrip(';').rstrip(')').rstrip('(').strip()
                    return table
            return None
        
        def _get_table_name(self, sql: str) -> str:
            """Get table name for simple queries"""
            return self._extract_table_name(sql)
        
        def fetchone(self):
            """Fetch one row"""
            if self._result and len(self._result) > 0:
                row = self._result[0]
                self._result = self._result[1:]
                return row
            return None
        
        def fetchall(self):
            """Fetch all rows"""
            result = self._result
            self._result = []
            return result
        
        def fetchmany(self, size=1):
            """Fetch many rows"""
            if size <= 0:
                return []
            result = self._result[:size]
            self._result = self._result[size:]
            return result
        
        @property
        def rowcount(self):
            return self._rowcount
        
        @property
        def lastrowid(self):
            return self._lastrowid
        
        def __iter__(self):
            for row in self._result:
                yield row
        
        def __next__(self):
            if not self._result:
                raise StopIteration
            return self._result.pop(0)
    
    def get_cursor(self, conn=None):
        """Get a cursor for the connection"""
        # If conn is provided, use it as the Supabase connection
        if conn and hasattr(conn, 'table'):
            return self._SupabaseCursor(conn)
        # Otherwise, use the stored connection
        return self._SupabaseCursor(self._conn) if self._conn else None
    
    def get_connection(self):
        """Get a connection - required by crud_operations.py"""
        try:
            # Try to get Supabase connection from Streamlit
            if 'supabase' in st.connections:
                self._conn = st.connections.supabase
            else:
                # Initialize Supabase connection
                from st_supabase_connection import SupabaseConnection
                self._conn = st.connection("supabase", type=SupabaseConnection)
            
            # Test the connection
            test_result = self._conn.table('users').select('id').limit(1).execute()
            print("✅ Supabase connection successful")
            return self
            
        except Exception as e:
            print(f"❌ Supabase connection error: {e}")
            # Fallback to mock connection for testing
            self._conn = self._MockSupabase()
            return self
    
    class _MockSupabase:
        """Mock Supabase for testing when connection fails"""
        def table(self, table_name):
            return self._MockTable(table_name)
        
        class _MockTable:
            def __init__(self, table_name):
                self.table_name = table_name
            
            def select(self, *args):
                return self
            
            def insert(self, data):
                return self
            
            def update(self, data):
                return self
            
            def delete(self):
                return self
            
            def eq(self, col, val):
                return self
            
            def order(self, col, desc=False):
                return self
            
            def limit(self, n):
                return self
            
            def execute(self):
                return self._MockResponse()
            
            class _MockResponse:
                data = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # No cleanup needed for Supabase connections
        pass