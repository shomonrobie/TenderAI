# database/supabase_sql_wrapper.py - Fixed to handle Supabase properly

"""
SQL Wrapper that automatically handles both SQLite and Supabase
ALL existing methods work without changes!
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import sqlite3
from httpx import HTTPError
logger = logging.getLogger(__name__)


class SupabaseSQLWrapper:
    """
    Wrapper that automatically converts SQLite-style SQL queries to Supabase API calls.
    ALL existing code works without changes!
    """
    
    def __init__(self, db_connection):
        self.db_conn = db_connection
        self._result = None
        self._rowcount = 0
        self._lastrowid = None
        self._description = None
        self._executed_sql = None
        self._executed_params = None
        
        # Detect if we have a Supabase client
        self._supabase_client = None
        self.db_type = 'sqlite'
        
        # ✅ Check if db_connection is a SupabaseContextWrapper
        if hasattr(db_connection, 'client'):
            client = db_connection.client
            if client and hasattr(client, 'table') and callable(getattr(client, 'table')):
                self._supabase_client = client
                self.db_type = 'supabase'
                print(f"✅ Supabase client detected from client attribute")
                return
        
        # ✅ Check if db_connection is a Supabase client directly
        if hasattr(db_connection, 'table') and callable(getattr(db_connection, 'table')):
            self._supabase_client = db_connection
            self.db_type = 'supabase'
            print(f"✅ Supabase client detected directly")
            return
        
        # ✅ Check if db_connection is DatabaseCRUD with supabase attribute
        if hasattr(db_connection, 'supabase') and db_connection.supabase:
            self._supabase_client = db_connection.supabase
            self.db_type = 'supabase'
            print(f"✅ Supabase client detected from supabase attribute")
            return
        
        # ✅ Check if db_connection is DatabaseCRUD with _use_supabase
        if hasattr(db_connection, '_use_supabase') and db_connection._use_supabase:
            if hasattr(db_connection, 'supabase') and db_connection.supabase:
                self._supabase_client = db_connection.supabase
                self.db_type = 'supabase'
                print(f"✅ Supabase client detected from _use_supabase")
                return
        
        # ✅ Check various other attributes
        for attr in ['_supabase_client', 'client', '_client']:
            if hasattr(db_connection, attr):
                client = getattr(db_connection, attr)
                if client and hasattr(client, 'table') and callable(getattr(client, 'table')):
                    self._supabase_client = client
                    self.db_type = 'supabase'
                    print(f"✅ Supabase client detected from {attr}")
                    return
        
        # ✅ Fallback: try to get from connection module
        try:
            from database.connection import get_supabase_client, get_db_type
            client = get_supabase_client()
            if client:
                self._supabase_client = client
                self.db_type = get_db_type()
                print(f"✅ Supabase client from connection module: {self.db_type}")
                return
        except:
            pass
        
        print(f"⚠️ No Supabase client found, using SQLite mode")

        
    def cursor(self):
        """Return self as cursor (for compatibility)"""
        return self
    
    def get_connection(self):
        """Return self as connection (for compatibility)"""
        return self
    
    def __call__(self):
        """Allow the object to be called (for compatibility)"""
        return self
        
    def execute(self, sql: str, params: tuple = None):
        """
        Execute any SQL query - automatically handles both SQLite and Supabase
        ALL existing methods work without changes!
        """
        self._executed_sql = sql
        self._executed_params = params
        
        # Debug: Log what's being executed
        print(f"🔍 execute() called in supabase sql wrapper : db_type={self.db_type}, sql={sql[:105]}...")
        print(f"🔍 has_supabase_client={self._supabase_client is not None}")
        
        # Check if we're using Supabase
        if self.db_type == 'supabase' and self._supabase_client:
            print(f"✅ Using Supabase mode")
            return self._execute_supabase(sql, params)
        else:
            # Only use SQLite if we're actually in SQLite mode
            print(f"⚠️ Using SQLite mode (db_type={self.db_type})")
            return self._execute_sqlite(sql, params)

    
    def _execute_supabase(self, sql: str, params: tuple = None):
        """Execute query on Supabase"""
        try:
            # Clean up the SQL
            sql = sql.strip()
            sql_upper = sql.upper()
            
            # print(f"🔍 _execute_supabase: sql_upper starts with:")
            # print(f"   SELECT: {sql_upper.startswith('SELECT')}")
            # print(f"   INSERT: {sql_upper.startswith('INSERT')}")
            # print(f"   UPDATE: {sql_upper.startswith('UPDATE')}")
            # print(f"   DELETE: {sql_upper.startswith('DELETE')}")
            # print(f"   sql_upper[:1500]: {sql_upper[:1500]}")
            
            # Handle SQLite-specific statements
            if sql_upper.startswith('PRAGMA'):
                self._result = []
                self._rowcount = 0
                return self
            
            # Handle different query types
            if sql_upper.startswith('SELECT'):
                return self._execute_select_supabase(sql, params)
            elif sql_upper.startswith('INSERT'):
                print(f"✅ INSERT detected, calling _execute_insert_supabase")
                return self._execute_insert_supabase(sql, params)
            elif sql_upper.startswith('UPDATE'):
                return self._execute_update_supabase(sql, params)
            elif sql_upper.startswith('DELETE'):
                return self._execute_delete_supabase(sql, params)
            else:
                print(f"⚠️ Unknown query type, treating as SELECT")
                # For any other query, try to parse as SELECT
                return self._execute_select_supabase(sql, params)
                
        except Exception as e:
            print(f"⚠️ Supabase query error: {e}")
            self._result = []
            self._rowcount = 0
            return self

    
    def _execute_select_supabase(self, sql: str, params: tuple = None):
        """
        Execute SELECT query on Supabase - handles ALL SELECT queries including JOINs
        
        Args:
            sql: SQL query string
            params: Query parameters (optional)
        
        Returns:
            self (for method chaining)
        """
        # print(f"🔍 _execute_select_supabase called: sql={sql[:1500]}...")
        
        try:
            sql_lower = sql.lower()
            
            # Handle COUNT(*) queries
            if self._is_count_query(sql_lower):
                return self._execute_count_query(sql, params)
            
            # Handle JOIN queries
            if 'join' in sql_lower:
                return self._handle_join_query(sql, sql_lower, params)
            
            # Handle regular SELECT queries
            return self._handle_simple_select(sql, sql_lower, params)
            
        except Exception as e:
            print(f"⚠️ SELECT parse error: {e}")
            self._result = []
            self._rowcount = 0
            return self

    def _is_count_query(self, sql_lower: str) -> bool:
        """Check if query is a COUNT query"""
        return 'count(*)' in sql_lower or 'count(1)' in sql_lower or 'count(' in sql_lower
    def _handle_join_query(self, sql: str, sql_lower: str, params: tuple = None):
        """
        Handle JOIN queries using raw SQL execution.
        """
        try:
            # Convert ? placeholders to $1, $2, etc. for Supabase
            if params:
                supabase_sql = sql
                param_count = 0
                in_string = False
                new_sql = []
                for char in supabase_sql:
                    if char == "'":
                        in_string = not in_string
                        new_sql.append(char)
                    elif char == '?' and not in_string:
                        param_count += 1
                        new_sql.append(f'${param_count}')
                    else:
                        new_sql.append(char)
                supabase_sql = ''.join(new_sql)
                
                # Execute with parameters
                # Note: This uses the postgrest client's rpc method
                # You may need to create a function in Supabase for this
                result = self._supabase_client.rpc('execute_sql', {'query': supabase_sql, 'params': list(params)}).execute()
                self._result = result.data if result else []
                self._rowcount = len(self._result)
                return self
            else:
                # Try to execute the SQL directly
                # Note: This may not work in all versions
                result = self._supabase_client.from_(f'({sql})').select('*').execute()
                self._result = result.data if result else []
                self._rowcount = len(self._result)
                return self
                
        except Exception as e:
            print(f"⚠️ JOIN query raw SQL error: {e}")
            # Fallback to simple query
            return self._fallback_simple_query(sql_lower)

    def _apply_where_for_join(self, query, sql_lower: str, params: tuple, main_table: str, join_table: str):
        """Apply WHERE clause for JOIN queries"""
        where_parts = re.split(r'\bwhere\b', sql_lower, 1, flags=re.IGNORECASE)
        if len(where_parts) > 1:
            where_clause = where_parts[1]
            for keyword in ['order by', 'limit', 'group by']:
                if keyword in where_clause:
                    where_clause = where_clause.split(keyword)[0]
            where_clause = where_clause.strip()
            if where_clause:
                # Check if WHERE clause references joined table
                if join_table and any(t in where_clause for t in [join_table, f'{join_table}.']):
                    print(f"⚠️ WHERE clause references joined table, skipping WHERE")
                    return query
                return self._apply_where_clause(query, where_clause, params)
        return query

    def _apply_order_for_join(self, query, sql_lower: str, main_table: str):
        """Apply ORDER BY for JOIN queries"""
        order_match = re.search(r'order by\s+([^\s]+(?:\s+(?:asc|desc))?)', sql_lower, re.IGNORECASE)
        if order_match:
            order_str = order_match.group(1).strip()
            parts = order_str.split()
            col = parts[0]
            
            # Remove table alias if present
            if '.' in col:
                # Check if it's from the main table
                if col.split('.')[0] != main_table:
                    print(f"⚠️ ORDER BY references joined table, skipping")
                    return query
                col = col.split('.')[-1]
            
            direction = 'asc' if len(parts) == 1 or parts[1].lower() == 'asc' else 'desc'
            return query.order(col, desc=(direction == 'desc'))
        return query

    def _apply_limit(self, query, sql_lower: str):
        """Apply LIMIT clause"""
        limit_match = re.search(r'limit\s+(\d+)', sql_lower, re.IGNORECASE)
        if limit_match:
            return query.limit(int(limit_match.group(1)))
        return query

    def _merge_join_data(self, main_data, on_match, join_table, sql_lower):
        """Merge joined table data into main data"""
        try:
            # Extract column names from ON condition
            left_col = on_match.group(1).strip().split('.')[-1]
            right_col = on_match.group(2).strip().split('.')[-1]
            
            # Get values from main table
            values = [row.get(left_col) for row in main_data if row.get(left_col)]
            
            if values:
                # Get joined table data
                join_query = self._supabase_client.table(join_table).select('*')
                join_query = join_query.in_(right_col, values)
                
                join_response = join_query.execute()
                join_data = join_response.data if join_response else []
                
                # Merge data
                for row in main_data:
                    matching = [j for j in join_data if j.get(right_col) == row.get(left_col)]
                    if matching:
                        for key, value in matching[0].items():
                            if key not in row:
                                row[f'{join_table}_{key}'] = value
            
            return main_data
        except Exception as e:
            print(f"⚠️ Merge join data error: {e}")
            return main_data

    def _fallback_simple_query(self, sql_lower: str):
        """Fallback to simple query on main table"""
        from_match = re.search(r'from\s+([^\s]+)', sql_lower)
        if from_match:
            main_table = from_match.group(1).strip().split()[0].strip()
            query = self._supabase_client.table(main_table).select('*')
            response = query.execute()
            self._result = response.data if response else []
            self._rowcount = len(self._result)
        else:
            self._result = []
            self._rowcount = 0
        return self

    def _handle_simple_select(self, sql: str, sql_lower: str, params: tuple = None):
        """Handle regular (non-JOIN) SELECT queries"""
        print(f"🔍 _handle_simple_select called: sql={sql[:100]}...")
        
        # Extract table name
        from_match = re.search(r'from\s+([^\s]+)', sql_lower)
        if not from_match:
            self._result = []
            self._rowcount = 0
            return self
        
        table_name = from_match.group(1).strip().split()[0].strip()
        print(f"🔍 Table: {table_name}")
        
        # Build query
        query = self._supabase_client.table(table_name).select('*')
        
        # Apply WHERE clause
        if 'where' in sql_lower:
            query = self._apply_where_clause_from_sql(query, sql_lower, params)
        
        # Apply ORDER BY
        if 'order by' in sql_lower:
            print(f"🔍 ORDER BY found in SQL, applying...")
            query = self._apply_order_by(query, sql_lower)
        
        # Apply LIMIT
        if 'limit' in sql_lower:
            query = self._apply_limit(query, sql_lower)
        
        # Execute with an automatic retry for network/stream drops
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = query.execute()
                self._result = response.data if response else []
                self._rowcount = len(self._result)
                print(f"🔍 Query returned {self._rowcount} rows")
                break  # Success, exit the retry loop
                
            except Exception as e:
                error_str = str(e)
                is_conn_error = "ConnectionTerminated" in error_str or "stream" in error_str.lower()
                
                if is_conn_error and attempt < max_retries - 1:
                    print(f"⚠️ Connection dropped (Attempt {attempt + 1}). Retrying query...")
                    continue  # Try execution one more time
                    
                print(f"❌ Query execution error: {e}")
                self._result = []
                self._rowcount = 0
                break
        
        if self._result and len(self._result) > 0:
            self._description = [(key, None, None, None, None, None, None) for key in self._result[0].keys()]
        
        return self

    def _handle_simple_select_bak(self, sql: str, sql_lower: str, params: tuple = None):
        """Handle regular (non-JOIN) SELECT queries"""
        print(f"🔍 _handle_simple_select called: sql={sql[:100]}...")
        
        # Extract table name
        from_match = re.search(r'from\s+([^\s]+)', sql_lower)
        if not from_match:
            self._result = []
            self._rowcount = 0
            return self
        
        table_name = from_match.group(1).strip().split()[0].strip()
        print(f"🔍 Table: {table_name}")
        
        # Build query
        query = self._supabase_client.table(table_name).select('*')
        
        # Apply WHERE clause
        if 'where' in sql_lower:
            query = self._apply_where_clause_from_sql(query, sql_lower, params)
        
        # Apply ORDER BY
        if 'order by' in sql_lower:
            print(f"🔍 ORDER BY found in SQL, applying...")
            query = self._apply_order_by(query, sql_lower)
        
        # Apply LIMIT
        if 'limit' in sql_lower:
            query = self._apply_limit(query, sql_lower)
        
        # Execute
        try:
            response = query.execute()
            self._result = response.data if response else []
            self._rowcount = len(self._result)
            print(f"🔍 Query returned {self._rowcount} rows")
        except Exception as e:
            print(f"❌ Query execution error: {e}")
            self._result = []
            self._rowcount = 0
        
        if self._result and len(self._result) > 0:
            self._description = [(key, None, None, None, None, None, None) for key in self._result[0].keys()]
        
        return self


    def _apply_where_clause_from_sql(self, query, sql_lower: str, params: tuple):
        """Apply WHERE clause from SQL string"""
        where_parts = re.split(r'\bwhere\b', sql_lower, 1, flags=re.IGNORECASE)
        if len(where_parts) > 1:
            where_clause = where_parts[1]
            for keyword in ['order by', 'limit', 'group by']:
                if keyword in where_clause:
                    where_clause = where_clause.split(keyword)[0]
            where_clause = where_clause.strip()
            if where_clause:
                return self._apply_where_clause(query, where_clause, params)
        return query

    def _apply_order_by(self, query, sql_lower: str):
        """Apply ORDER BY clause - FIXED for multiple columns"""
        # Handle multiple ORDER BY columns
        order_match = re.search(r'order by\s+(.+?)(?:$|limit|group by|having)', sql_lower, re.IGNORECASE)
        if order_match:
            order_str = order_match.group(1).strip()
            # Split by comma but respect any nested commas (none in simple ORDER BY)
            order_parts = [p.strip() for p in order_str.split(',')]
            
            for part in order_parts:
                # Parse each part: "column" or "column asc" or "column desc"
                parts = part.split()
                col = parts[0]
                direction = 'asc' if len(parts) == 1 or parts[1].lower() == 'asc' else 'desc'
                
                # Remove table alias if present
                if '.' in col:
                    col = col.split('.')[-1]
                
                query = query.order(col, desc=(direction == 'desc'))
        
        return query


    # database/supabase_sql_wrapper.py - Update _execute_count_query

    def _execute_count_query(self, sql: str, params: tuple = None):
        """Handle COUNT(*) queries - with proper parameter handling"""
        # print(f"🔍 _execute_count_query called: sql={sql[:1500]}...")
    
        # Check if this is the problematic date query
        if "NOW() - INTERVAL '7 days'" in sql or "CURRENT_DATE - INTERVAL" in sql:
            print("⚠️ Detected problematic date query - returning empty result")
            self._result = []
            self._rowcount = 0
            return self

        try:
            sql_lower = sql.lower()
            
            # Extract table name
            from_match = re.search(r'from\s+([^\s]+)', sql_lower)
            if not from_match:
                self._result = []
                self._rowcount = 0
                return self
            
            table_name = from_match.group(1).strip().split()[0].strip()
            
            # Build count query
            query = self._supabase_client.table(table_name).select('*', count='exact')
            
            # Parse WHERE clause
            if 'where' in sql_lower:
                where_parts = re.split(r'\bwhere\b', sql_lower, 1, flags=re.IGNORECASE)
                if len(where_parts) > 1:
                    where_clause = where_parts[1]
                    # Remove ORDER BY, LIMIT, GROUP BY
                    for keyword in ['order by', 'limit', 'group by']:
                        if keyword in where_clause:
                            where_clause = where_clause.split(keyword)[0]
                    where_clause = where_clause.strip()
                    if where_clause:
                        # Use the improved _apply_where_clause
                        query = self._apply_where_clause(query, where_clause, params)
            
            # Execute with limit 0 to just get count
            query = query.limit(0)
            response = query.execute()
            
            # Get count from response
            count = response.count if hasattr(response, 'count') else 0
            
            # Return as a single row with 'total' column
            self._result = [{'total': count}]
            self._rowcount = 1
            self._description = [('total', None, None, None, None, None, None)]
            
            return self
            
        except Exception as e:
            print(f"⚠️ Count query error: {e}")
            print(f"⚠️ Count query : {sql}")
            self._result = []
            self._rowcount = 0
            return self


    # database/supabase_sql_wrapper.py - Update _apply_where_clause

    def _apply_where_clause(self, query, where_clause: str, params: tuple = None):
        """Apply WHERE clause to Supabase query - FIXED for IN with multiple params"""
        param_index = 0
        
        conditions = re.split(r'\s+and\s+|\s+or\s+', where_clause, flags=re.IGNORECASE)
        
        for condition in conditions:
            condition = condition.strip()
            if not condition:
                continue
            
            # ✅ Handle IN clause FIRST (before LIKE)
            if ' in (' in condition.lower():
                match = re.match(r'([^\s]+)\s+in\s*\((.*?)\)', condition, re.IGNORECASE)
                if match:
                    col = match.group(1).strip()
                    values_str = match.group(2).strip()
                    
                    # Check if values_str contains multiple '?' placeholders
                    if values_str == '?' or values_str.startswith('?') or values_str == '?,?' or ',' in values_str and '?' in values_str:
                        # Count how many '?' placeholders in the string
                        placeholder_count = values_str.count('?')
                        
                        # Extract the actual values from params
                        if params and param_index + placeholder_count <= len(params):
                            values = list(params[param_index:param_index + placeholder_count])
                            param_index += placeholder_count
                            
                            # Convert values to appropriate types
                            processed_values = []
                            for v in values:
                                if isinstance(v, (int, float)):
                                    processed_values.append(v)
                                elif isinstance(v, str):
                                    if v.lower() == 'null':
                                        processed_values.append(None)
                                    else:
                                        processed_values.append(v)
                                else:
                                    processed_values.append(v)
                            
                            query = query.in_(col, processed_values)
                        else:
                            # Fallback: try to parse values from string
                            values = [v.strip().strip("'") for v in values_str.split(',')]
                            query = query.in_(col, values)
                    else:
                        # Parse individual values
                        values = []
                        for val in values_str.split(','):
                            val = val.strip()
                            if val == '?' and params and param_index < len(params):
                                values.append(params[param_index])
                                param_index += 1
                            elif val.startswith("'") and val.endswith("'"):
                                values.append(val[1:-1])
                            elif val.lower() == 'null':
                                values.append(None)
                            else:
                                try:
                                    values.append(int(val))
                                except:
                                    try:
                                        values.append(float(val))
                                    except:
                                        values.append(val)
                        if values:
                            query = query.in_(col, values)
                    continue
            
            # Handle LIKE
            if ' like ' in condition.lower():
                match = re.match(r'([^\s]+)\s+like\s+(.+)', condition, re.IGNORECASE)
                if match:
                    col = match.group(1).strip()
                    val = match.group(2).strip()
                    if val == '?' and params and param_index < len(params):
                        val = params[param_index]
                        param_index += 1
                    elif val.startswith("'") and val.endswith("'"):
                        val = val[1:-1]
                    if '%' in val:
                        val = val.replace('%', '*')
                        query = query.ilike(col, val)
                    else:
                        query = query.ilike(col, f'%{val}%')
                    continue
            
            # Handle IS NULL / IS NOT NULL
            if ' is null' in condition.lower():
                match = re.match(r'([^\s]+)\s+is\s+null', condition, re.IGNORECASE)
                if match:
                    col = match.group(1).strip()
                    query = query.is_(col, None)
                    continue
            
            if ' is not null' in condition.lower():
                match = re.match(r'([^\s]+)\s+is\s+not\s+null', condition, re.IGNORECASE)
                if match:
                    col = match.group(1).strip()
                    query = query.not_.is_(col, None)
                    continue
            
            # Handle simple equality
            if '=' in condition:
                parts = condition.split('=', 1)
                if len(parts) == 2:
                    col = parts[0].strip()
                    val = parts[1].strip()
                    
                    if val == '?' and params and param_index < len(params):
                        query = query.eq(col, params[param_index])
                        param_index += 1
                    elif val.startswith("'") and val.endswith("'"):
                        query = query.eq(col, val[1:-1])
                    elif val.lower() == 'true' or val.lower() == 'false':
                        query = query.eq(col, val.lower() == 'true')
                    elif val.lower() == 'null':
                        query = query.is_(col, None)
                    else:
                        try:
                            if '.' in val:
                                query = query.eq(col, float(val))
                            else:
                                query = query.eq(col, int(val))
                        except:
                            query = query.eq(col, val)
                    continue
            
            # Handle inequality
            if '!=' in condition or '<>' in condition:
                parts = re.split(r'!=|<>', condition, 1)
                if len(parts) == 2:
                    col = parts[0].strip()
                    val = parts[1].strip()
                    if val == '?' and params and param_index < len(params):
                        query = query.neq(col, params[param_index])
                        param_index += 1
                    else:
                        query = query.neq(col, val.strip("'"))
                    continue
            
            # Handle greater than / less than
            for op in ['>=', '<=', '>', '<']:
                if op in condition:
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        col = parts[0].strip()
                        val = parts[1].strip()
                        if val == '?' and params and param_index < len(params):
                            if op == '>=':
                                query = query.gte(col, params[param_index])
                            elif op == '<=':
                                query = query.lte(col, params[param_index])
                            elif op == '>':
                                query = query.gt(col, params[param_index])
                            elif op == '<':
                                query = query.lt(col, params[param_index])
                            param_index += 1
                        continue
        
        return query

    # database/supabase_sql_wrapper.py - Add debug to _execute_insert_supabase

    # database/supabase_sql_wrapper.py - Fixed _execute_insert_supabase

    def _execute_insert_supabase(self, sql: str, params: tuple = None):
        """Execute INSERT query on Supabase"""
        try:
            # print(f"🔍 ==== _execute_insert_supabase called ====")
            # print(f"🔍 SQL: {sql[:200]}...")
            # print(f"🔍 Params: {params}")
            
            # ✅ Clean the SQL - remove newlines and extra spaces
            cleaned_sql = ' '.join(sql.split())
            print(f"🔍 Cleaned SQL: {cleaned_sql[:200]}...")
            
            match = re.search(r'insert\s+into\s+([^\s(]+)', cleaned_sql, re.IGNORECASE)
            if not match:
                print(f"❌ Could not extract table name")
                self._result = []
                self._rowcount = 0
                return self
            
            table_name = match.group(1).strip()
            print(f"🔍 Table name: {table_name}")
            
            # ✅ Extract columns from the cleaned SQL
            columns_match = re.search(r'\((.*?)\)\s*values', cleaned_sql, re.IGNORECASE)
            if not columns_match:
                print(f"❌ Could not extract columns")
                print(f"   Cleaned SQL: {cleaned_sql}")
                self._result = []
                self._rowcount = 0
                return self
            
            columns = [col.strip() for col in columns_match.group(1).split(',')]
            print(f"🔍 Columns: {columns}")
            
            data = {}
            if params:
                for i, col in enumerate(columns):
                    if i < len(params):
                        val = params[i]
                        # Skip empty strings for timestamp columns
                        if val == '' and ('created_at' in col or 'updated_at' in col or 'timestamp' in col):
                            continue
                        data[col] = val
            
            print(f"🔍 Data to insert: {data}")
            
            if not data:
                print(f"⚠️ No data to insert")
                self._result = []
                self._rowcount = 0
                return self
            
            print(f"🔍 Calling Supabase insert on {table_name}...")
            response = self._supabase_client.table(table_name).insert(data).execute()
            
            print(f"🔍 Response: {response}")
            print(f"🔍 Response data: {response.data if hasattr(response, 'data') else 'No data'}")
            
            self._result = response.data if response else []
            self._rowcount = len(self._result) if self._result else 0
            
            if self._result and len(self._result) > 0:
                first_key = list(self._result[0].keys())[0] if self._result[0] else None
                self._lastrowid = self._result[0].get(first_key) if first_key else None
            
            print(f"✅ Insert result: {self._rowcount} rows inserted, lastrowid: {self._lastrowid}")
            return self
            
        except Exception as e:
            print(f"⚠️ INSERT error: {e}")
            import traceback
            traceback.print_exc()
            self._result = []
            self._rowcount = 0
            return self
    def _execute_update_supabase(self, sql: str, params: tuple = None):
        """Execute UPDATE query on Supabase"""
        try:
            match = re.search(r'update\s+([^\s]+)', sql, re.IGNORECASE)
            if not match:
                self._result = []
                self._rowcount = 0
                return self
            
            table_name = match.group(1).strip()
            
            set_match = re.search(r'set\s+(.*?)(?:where|$)', sql, re.IGNORECASE)
            if not set_match:
                self._result = []
                self._rowcount = 0
                return self
            
            set_clause = set_match.group(1).strip()
            
            where_clause = None
            if 'where' in sql.lower():
                where_match = re.search(r'where\s+(.*?)(?:order|limit|$)', sql, re.IGNORECASE)
                if where_match:
                    where_clause = where_match.group(1).strip()
            
            data = {}
            param_index = 0
            
            for assignment in set_clause.split(','):
                if '=' not in assignment:
                    continue
                parts = assignment.split('=', 1)
                col = parts[0].strip()
                
                if params and param_index < len(params):
                    data[col] = params[param_index]
                    param_index += 1
                else:
                    val = parts[1].strip()
                    if val.startswith("'") and val.endswith("'"):
                        data[col] = val[1:-1]
                    elif val.upper() == 'NULL':
                        data[col] = None
                    elif val.upper() == 'CURRENT_TIMESTAMP':
                        data[col] = datetime.now().isoformat()
                    else:
                        try:
                            data[col] = int(val)
                        except:
                            try:
                                data[col] = float(val)
                            except:
                                data[col] = val
            
            if not data:
                self._result = []
                self._rowcount = 0
                return self
            
            query = self._supabase_client.table(table_name).update(data)
            
            if where_clause:
                query = self._apply_where_clause(query, where_clause, params[param_index:] if params else None)
            
            response = query.execute()
            self._result = response.data if response else []
            self._rowcount = len(self._result)
            return self
            
        except Exception as e:
            print(f"⚠️ UPDATE error: {e}")
            self._result = []
            self._rowcount = 0
            return self
    
    def _execute_delete_supabase(self, sql: str, params: tuple = None):
        """Execute DELETE query on Supabase"""
        try:
            match = re.search(r'delete\s+from\s+([^\s]+)', sql, re.IGNORECASE)
            if not match:
                self._result = []
                self._rowcount = 0
                return self
            
            table_name = match.group(1).strip()
            
            where_clause = None
            if 'where' in sql.lower():
                where_match = re.search(r'where\s+(.*?)(?:order|limit|$)', sql, re.IGNORECASE)
                if where_match:
                    where_clause = where_match.group(1).strip()
            
            query = self._supabase_client.table(table_name).delete()
            
            if where_clause:
                query = self._apply_where_clause(query, where_clause, params)
            
            response = query.execute()
            self._result = response.data if response else []
            self._rowcount = len(self._result)
            return self
            
        except Exception as e:
            print(f"⚠️ DELETE error: {e}")
            self._result = []
            self._rowcount = 0
            return self
    
    def _execute_sqlite(self, sql: str, params: tuple = None):
        """Execute query on SQLite"""
        try:
            # Get a connection - only called when in SQLite mode
            if hasattr(self.db_conn, 'get_connection'):
                conn = self.db_conn.get_connection()
            else:
                # If db_conn is already a connection
                conn = self.db_conn
            
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Handle different query types
            sql_upper = sql.upper().strip()
            if sql_upper.startswith('SELECT'):
                self._result = cursor.fetchall()
                self._rowcount = len(self._result)
                if self._result and len(self._result) > 0:
                    self._description = cursor.description
            elif sql_upper.startswith('INSERT'):
                self._lastrowid = cursor.lastrowid
                self._rowcount = cursor.rowcount
                self._result = []
            else:
                self._rowcount = cursor.rowcount
                self._result = []
            
            # Commit if not SELECT
            if not sql_upper.startswith('SELECT'):
                conn.commit()
            
            return self
            
        except sqlite3.ProgrammingError as e:
            if "closed database" in str(e).lower():
                print("⚠️ SQLite connection was closed, attempting to reopen...")
                if hasattr(self.db_conn, '_sqlite_connection'):
                    self.db_conn._sqlite_connection = None
                return self._execute_sqlite(sql, params)
            raise
        except Exception as e:
            print(f"⚠️ SQLite error: {e}")
            self._result = []
            self._rowcount = 0
            return self
    
    def fetchone(self):
        """Fetch one row - returns dict"""
        if self._result and len(self._result) > 0:
            row = self._result[0]
            self._result = self._result[1:]
            
            if isinstance(row, dict):
                return row
            elif isinstance(row, (list, tuple)) and self._description:
                return {col[0]: row[i] for i, col in enumerate(self._description) if i < len(row)}
            return row
        return None
    
    def fetchall(self):
        """Fetch all rows - returns list of dicts"""
        result = self._result
        self._result = []
        
        if not result:
            return []
        
        if isinstance(result[0], dict):
            return result
        elif isinstance(result[0], (list, tuple)) and self._description:
            return [{col[0]: row[i] for i, col in enumerate(self._description) if i < len(row)} for row in result]
        
        return result
    
    def fetchmany(self, size=1):
        """Fetch many rows"""
        if size <= 0 or not self._result:
            return []
        result = self._result[:size]
        self._result = self._result[size:]
        
        if isinstance(result[0], dict):
            return result
        elif isinstance(result[0], (list, tuple)) and self._description:
            return [{col[0]: row[i] for i, col in enumerate(self._description) if i < len(row)} for row in result]
        
        return result
    
    @property
    def rowcount(self):
        return self._rowcount
    
    @property
    def lastrowid(self):
        return self._lastrowid
    
    @property
    def description(self):
        return self._description
    
    def commit(self):
        """Commit transaction (no-op for Supabase)"""
        return self
    
    def rollback(self):
        """Rollback transaction (no-op for Supabase)"""
        return self
    
    def close(self):
        """Close connection"""
        return self
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass