#database/crude_operations.py
import streamlit as st
import sqlite3
import json
import logging
import secrets
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Union
import bcrypt
import pandas as pd
from database.connection import get_connection, get_db_type, get_supabase_client, is_supabase
from database.supabase_sql_wrapper import SupabaseSQLWrapper
from database.crud_tender import TenderCRUD
from database.crud_rates import RateCRUD
from database.crud_boq import BOQCRUD
from database.crud_company import CompanyCRUD
# from database.crud_equipment import EquipmentCRUD
# from database.crud_experience import ExperienceCRUD
from database.crud_competitor import CompetitorCRUD
from database.crud_user import UserCRUD
from database.crud_system_rates import SystemRateCRUD
from database.crud_subscription import SubscriptionManager
from database.crud_autofill import AutoFillCRUD
from database.crud_role import RoleCRUD
import os
 

logger = logging.getLogger(__name__)

class DatabaseCRUD:
    """Handles all database CRUD operations"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        self.db_type = get_db_type()
        self._use_supabase = is_supabase()
        self.supabase = get_supabase_client() if self._use_supabase else None
        
        # ✅ Initialize CRUD modules
        self._subscription_crud = SubscriptionManager(self)
        self._user_crud = UserCRUD(self)
        self._role_crud = RoleCRUD(self)
        self._tender_crud = TenderCRUD(self)
        self._system_rate_crud = SystemRateCRUD(self)
        self._rate_crud = RateCRUD(self)
        self._boq_crud = BOQCRUD(self)
        self._company_crud = CompanyCRUD(self)
        # self._equipment_crud = EquipmentCRUD(self)
        # self._experience_crud = ExperienceCRUD(self)
        self._competitor_crud = CompetitorCRUD(self)
        self._autofill_crud = AutoFillCRUD(self)
        self._bind_competitor_methods()

        # ✅ Bind both Tender and Rate methods
        self._bind_subscription_methods()
        self._bind_user_methods()
        self._bind_role_methods()
        self._bind_tender_methods()
        self._bind_system_rate_methods()  # ✅ Make sure this is called!     
        self._bind_rate_methods()  # ✅ Make sure this is called!        
        self._bind_boq_methods()
        self._bind_company_methods()
        # self._bind_equipment_methods()
        # self._bind_experience_methods()
        self._bind_autofill_methods()
        print(f"✅ DatabaseCRUD initialized: mode={self.db_type}")
    
    
    def _bind_subscription_methods(self):
        """Bind all _subscription_crud methods to this instance"""
        # print("🔍 Binding _subscription_crud methods...")
        for method_name in dir(self._subscription_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._subscription_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                #print(f"   ✅ Bound: {method_name}")


    def _bind_user_methods(self):
        """Bind all UserCRUD methods to this instance"""
        # print("🔍 Binding UserCRUD methods...")
        for method_name in dir(self._user_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._user_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                #print(f"   ✅ Bound: {method_name}")

    
    def _bind_role_methods(self):
        """Bind all RoleCRUD methods to this instance"""
        # print("🔍 Binding RoleCRUD methods...")
        for method_name in dir(self._role_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._role_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                #print(f"   ✅ Bound: {method_name}")
    def _bind_tender_methods(self):
        """Bind all TenderCRUD methods to this instance"""
        for method_name in dir(self._tender_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._tender_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
    
    def _bind_system_rate_methods(self):
        """Bind all SystemRateCRUD methods to this instance"""
        # ✅ FIXED: Include private methods (those starting with _)
        for method_name in dir(self._system_rate_crud):
            # Skip only special methods like __init__, __str__, etc.
            if method_name.startswith('__') and method_name.endswith('__'):
                continue
            method = getattr(self._system_rate_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                # Debug: print what's being bound
                if method_name == '_update_version_stats':
                    print(f"   ✅ Bound: {method_name}")


    # def _bind_system_rate_methods(self):
    #     """Bind all RateCRUD methods to this instance"""
    #    #print("🔍 Binding RateCRUD methods...")
    #     for method_name in dir(self._system_rate_crud):
    #         if method_name.startswith('_'):
    #             continue
    #         method = getattr(self._system_rate_crud, method_name)
    #         if callable(method):
    #             setattr(self, method_name, method.__get__(self, DatabaseCRUD))
    #            # print(f"   ✅ Bound: {method_name}")
    
    def _bind_rate_methods(self):
        """Bind all RateCRUD methods to this instance"""
        #print("🔍 Binding RateCRUD methods...")
        for method_name in dir(self._rate_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._rate_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                #print(f"   ✅ Bound: {method_name}")

    def _bind_boq_methods(self):
        """Bind all BOQCRUD methods to this instance"""
        #print("🔍 Binding BOQCRUD methods...")
        for method_name in dir(self._boq_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._boq_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                #print(f"   ✅ Bound: {method_name}")

    def _bind_company_methods(self):
        """Bind company CRUD methods to DatabaseCRUD"""
        for method_name in dir(self._company_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._company_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
    
    

    def _bind_competitor_methods(self):
        """Bind all CompetitorCRUD methods to this instance"""
        # print("🔍 Binding CompetitorCRUD methods...")
        for method_name in dir(self._competitor_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._competitor_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))
                #print(f"   ✅ Bound: {method_name}")

    
    def _bind_autofill_methods(self):
        """Bind _autofill_crud methods to DatabaseCRUD"""
        for method_name in dir(self._autofill_crud):
            if method_name.startswith('_'):
                continue
            method = getattr(self._autofill_crud, method_name)
            if callable(method):
                setattr(self, method_name, method.__get__(self, DatabaseCRUD))

    def get_connection(self):
        """Returns a connection that supports context manager protocol"""
        if self._use_supabase:
            # ✅ Return the context wrapper, not the raw client
            from database.connection import SupabaseContextWrapper
            return SupabaseContextWrapper(get_connection())
        else:
            # SQLite connection
            return get_connection()
    
    def _get_db(self):
        """Return self for database operations (used by TenderCRUD)"""
        return self
    
    def get_cursor(self, conn=None):
        """Get cursor from connection"""
        if self._use_supabase:
            return SupabaseSQLWrapper(get_connection())
        else:
            if conn is None:
                conn = get_connection()
            return conn.cursor()
    
    
    def execute(self, sql: str, params: tuple = None) -> int:
        """Execute SQL with parameter substitution (database-agnostic)"""
        print(f"🔍 execute() called in crude Operations: db_type={self.db_type}, sql={sql[:100]}...")
        
        # ✅ Use self.supabase (not self.supabase_client)
        if self._use_supabase and self.supabase:
            try:
                wrapper = SupabaseSQLWrapper(self.get_connection())
                result = wrapper.execute(sql, params)
                if sql.strip().upper().startswith('SELECT'):
                    rows = wrapper.fetchall()
                    wrapper._result = rows
                    return len(rows) if rows else 0
                else:
                    return getattr(result, 'rowcount', 0)
            except Exception as e:
                print(f"❌ Supabase execute error: {e}")
                import traceback
                traceback.print_exc()
                return 0
        else:
            # SQLite path
            try:
                conn = self.get_connection()
                cursor = self.get_cursor(conn)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                if not sql.strip().upper().startswith('SELECT'):
                    conn.commit()
                return getattr(cursor, 'rowcount', 0)
            except Exception as e:
                print(f"❌ SQLite execute error: {e}")
                return 0


    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results as list of dicts"""
        print(f"🔍 query called: sql={sql[:50]}...")
        
        try:
            if self._use_supabase:
                # Use the wrapper properly
                wrapper = SupabaseSQLWrapper(self.get_connection())
                
                # Execute the query (this calls _execute_select_supabase internally)
                wrapper.execute(sql, params)
                
                # Fetch the results
                rows = wrapper.fetchall()
                print(f"🔍 query returned {len(rows) if rows else 0} rows")
                return rows if rows else []
            else:
                # SQLite path
                conn = self.get_connection()
                cursor = self.get_cursor(conn)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                rows = cursor.fetchall()
                if not rows:
                    return []
                try:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
                except:
                    return rows
        except Exception as e:
            print(f"❌ query error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def query_all(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        Execute query and return all results as list of dicts.
        This is an alias for query() for better readability.
        
        Args:
            sql: SQL query string with ? placeholders
            params: Tuple of parameters for the query
        
        Returns:
            List of dictionaries representing rows
        """
        print(f"🔍 query_all called: sql={sql[:50]}...")
        
        try:
            if self._use_supabase:
                # Use the wrapper properly
                wrapper = SupabaseSQLWrapper(self.get_connection())
                
                # Execute the query
                wrapper.execute(sql, params)
                
                # Fetch all results
                rows = wrapper.fetchall()
                print(f"🔍 query_all returned {len(rows) if rows else 0} rows")
                return rows if rows else []
            else:
                # SQLite path
                conn = self.get_connection()
                cursor = self.get_cursor(conn)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                rows = cursor.fetchall()
                if not rows:
                    return []
                
                # Convert to list of dicts
                try:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
                except:
                    return rows
        except Exception as e:
            print(f"❌ query_all error: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """Execute query and return single result"""
        results = self.query(sql, params)
        return results[0] if results else None
    
    
    
    # ====================== SCHEMA METHODS ======================
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        if self._use_supabase:
            try:
                response = self.supabase.table(table_name).select('*').limit(1).execute()
                return True
            except:
                return False
        else:
            result = self.query_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return result is not None
    
    def get_db_type(self):
        """Get database type"""
        return self.db_type

        # ==================== DATABASE-AGNOSTIC SCHEMA METHODS ====================
    
    
    def get_existing_tables(self):
        """Get list of existing tables (database-agnostic)"""
        db_type = self.db_type
        
        if db_type == 'sqlite':
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            results = self.query(sql)
            return {row['name'] if 'name' in row else list(row.values())[0] for row in results}
        
        elif db_type in ['postgresql', 'cockroachdb']:
            sql = """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
            results = self.query(sql)
            return {row['table_name'] for row in results}
        
        elif db_type == 'supabase':
            # ✅ Use the RPC function for Supabase
            try:
                from database.connection import get_supabase_client
                supabase = get_supabase_client()
                response = supabase.rpc("get_table_names").execute()
                
                if hasattr(response, 'data') and response.data:
                    return {row['table_name'] for row in response.data}
                else:
                    # Fallback to hardcoded list
                    return {
                        "users", "companies", "subscriptions", "user_oauth",
                        "boq_templates", "boq_items", "boq_approval_history",
                        "rates", "system_rates", "price_change_logs",
                        "company_profile", "company_onboarding_status", "company_documents",
                        "company_financials", "company_licenses", "company_personnel",
                        "company_nppi", "certificate",
                        "competitors", "competitor_rates", "competitor_master",
                        "competitor_bids", "competitor_bid_history",
                        "tenders", "tender_milestones", "tender_documents", "bid_submissions",
                        "analysis_history", "otp_verification", "system_config",
                        "user_activity_logs", "version_history", "migrations",
                        "pwd_import_history", "extension_downloads", "demo_data_generation_log"
                    }
            except Exception as e:
                logger.warning(f"Could not call get_table_names RPC: {e}")
                # Fallback to hardcoded list
                return {
                    "users", "companies", "subscriptions", "user_oauth",
                    "boq_templates", "boq_items", "boq_approval_history",
                    "rates", "system_rates", "price_change_logs",
                    "company_profile", "company_onboarding_status", "company_documents",
                    "company_financials", "company_licenses", "company_personnel",
                    "company_nppi", "certificate",
                    "competitors", "competitor_rates", "competitor_master",
                    "competitor_bids", "competitor_bid_history",
                    "tenders", "tender_milestones", "tender_documents", "bid_submissions",
                    "analysis_history", "otp_verification", "system_config",
                    "user_activity_logs", "version_history", "migrations",
                    "pwd_import_history", "extension_downloads", "demo_data_generation_log"
                }
        
        elif db_type == 'mysql':
            sql = "SHOW TABLES"
            results = self.query(sql)
            return {list(row.values())[0] for row in results}
        
        else:
            return set()

    
    def get_table_columns(self, table_name: str):
        """Get table columns (database-agnostic)"""
        db_type = self.db_type
        
        if db_type == 'sqlite':
            sql = f"PRAGMA table_info({table_name})"
            results = self.query(sql)
            return {row['name']: {
                'type': row['type'],
                'notnull': bool(row['notnull']),
                'default': row['dflt_value'],
                'pk': bool(row['pk'])
            } for row in results}
        
        elif db_type in ['postgresql', 'cockroachdb', 'supabase']:
            sql = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
            """
            results = self.query(sql, (table_name,))
            return {row['column_name']: {
                'type': row['data_type'],
                'notnull': row['is_nullable'] == 'NO',
                'default': row['column_default'],
                'pk': False
            } for row in results}
        
        elif db_type == 'mysql':
            sql = f"DESCRIBE {table_name}"
            results = self.query(sql)
            return {row['Field']: {
                'type': row['Type'],
                'notnull': row['Null'] == 'NO',
                'default': row['Default'],
                'pk': row['Key'] == 'PRI'
            } for row in results}
        
        return {}
    
    def get_existing_indexes(self):
        """Get existing indexes (database-agnostic)"""
        db_type = self.db_type
        
        if db_type == 'sqlite':
            sql = "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            results = self.query(sql)
            return {row['name']: row['tbl_name'] for row in results}
        
        elif db_type in ['postgresql', 'cockroachdb', 'supabase']:
            sql = """
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """
            results = self.query(sql)
            return {row['indexname']: row['tablename'] for row in results}
        
        elif db_type == 'mysql':
            sql = "SHOW INDEX FROM information_schema.statistics WHERE table_schema = DATABASE()"
            results = self.query(sql)
            return {row['Index_name']: row['Table'] for row in results}
        
        return {}
    
    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if column exists (database-agnostic)"""
        columns = self.get_table_columns(table_name)
        return column_name in columns
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists (database-agnostic)"""
        tables = self.get_existing_tables()
        return table_name in tables
    
    def add_column_if_not_exists(self, table_name: str, column_name: str, column_type: str) -> bool:
        """Add column if it doesn't exist (database-agnostic)"""
        if self.column_exists(table_name, column_name):
            return False
        
        db_type = self.db_type
        
        if db_type == 'sqlite':
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        elif db_type in ['postgresql', 'cockroachdb', 'supabase']:
            sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        elif db_type == 'mysql':
            sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        else:
            return False
        
        try:
            self.execute(sql)
            return True
        except Exception as e:
            print(f"⚠️ Failed to add column: {e}")
            return False

    # ==================== INTERNAL HELPER METHODS ====================
    
    def _row_to_dict(self, row, cursor=None):
        """Convert database row to dictionary"""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        if hasattr(row, 'keys'):
            return dict(row)
        try:
            if cursor and hasattr(cursor, 'description'):
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        except:
            pass
        return row
    
    def _normalize_row(self, row):
        """Normalize row to dictionary regardless of source"""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        if isinstance(row, (list, tuple)):
            return row
        if hasattr(row, '_asdict'):
            return row._asdict()
        if hasattr(row, '__dict__'):
            return row.__dict__
        return row

    # ==================== BACKWARD COMPATIBILITY ====================
    
    @property
    def db_conn(self):
        """Backward compatibility - returns a proxy to the connection"""
        print(f"🔍db_conn Backward compatibility  called")
        # print(f"   mode: {self.db_type}")
        class ConnectionProxy:
            def __init__(self, parent):
                self.parent = parent
            
            def get_cursor(self, conn=None):
                return self.parent.get_cursor(conn)
            
            def get_connection(self):
                return self.parent.get_connection()
        
        return ConnectionProxy(self)

    # ==================== HELPER METHODS ====================
    
    # def validate_bangladesh_mobile(self, mobile: str) -> bool:
    #     """Validate Bangladeshi mobile number"""
    #     if not mobile:
    #         return False
    #     mobile = re.sub(r'[\s\-+]', '', mobile)
    #     if mobile.startswith('88'):
    #         mobile = mobile[2:]
    #     pattern = r'^01[3-9]\d{8}$'
    #     return bool(re.match(pattern, mobile))
    
    # def normalize_mobile(self, mobile: str) -> str:
    #     """Normalize mobile number to standard format"""
    #     if not mobile:
    #         return mobile
    #     mobile = re.sub(r'[\s\-+]', '', mobile)
    #     if mobile.startswith('+88'):
    #         mobile = mobile[3:]
    #     elif mobile.startswith('88'):
    #         mobile = mobile[2:]
    #     return mobile

    def create_user(self, company_id: int, user_data: Dict, created_by: int = None) -> tuple:
        """
        Create a new user with unique mobile number and email
        
        Args:
            company_id: Company ID (can be None for system users)
            user_data: Dict with keys: username, password, email, full_name, phone, mobile_number, role
            created_by: User ID of creator
        
        Returns:
            (success: bool, message: str or user_id: int)
        """
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Validate required fields
            if not user_data.get('username'):
                return False, "Username is required"
            if not user_data.get('password'):
                return False, "Password is required"
            if not user_data.get('email'):
                return False, "Email is required"
            if not user_data.get('mobile_number'):
                return False, "Mobile number is required"
            
            # Validate mobile number format
            mobile = self.normalize_mobile(user_data['mobile_number'])
            if not self.validate_bangladesh_mobile(mobile):
                return False, f"Invalid mobile number: {mobile}. Must be 11 digits starting with 01"
            
            # Check if mobile number already exists
            cursor.execute("SELECT id FROM users WHERE mobile_number = ?", (mobile,))
            if cursor.fetchone():
                return False, f"Mobile number {mobile} is already registered"
            
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (user_data['email'],))
            if cursor.fetchone():
                return False, f"Email {user_data['email']} is already registered"
            
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (user_data['username'],))
            if cursor.fetchone():
                return False, f"Username {user_data['username']} is already taken"
            
            # Hash password
            hashed = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Set default role if not provided
            role = user_data.get('role', 'viewer')
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, mobile_number,
                    role, is_active, is_approved, created_by, created_at, account_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                company_id,
                user_data['username'],
                hashed,
                user_data['email'],
                user_data.get('full_name', ''),
                user_data.get('phone', ''),
                mobile,
                role,
                1,  # is_active
                1,  # is_approved (auto-approved for company users)
                created_by,
                'company'
            ))
            
            user_id = cursor.lastrowid
            return True, user_id
    # ====================== GOOGLE USER METHODS ======================
    # database/crud_operations.py - Fixed methods for both SQLite and Supabase

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address"""
        # ✅ Use query_one - works for both SQLite and Supabase
        return self.query_one("""
            SELECT id, username, email, full_name, role, company_id, is_active,
                created_at, last_login
            FROM users WHERE email = ?
        """, (email,))

    # def authenticate_user(self, username_or_email: str, password: str) -> Optional[Dict]:
    #     """
    #     Authenticate user - supports both SHA256 and bcrypt hashes
    #     Works with both SQLite and Supabase
    #     """
    #     try:
    #         # ✅ Use separate queries to avoid parser issues
    #         # First try username
    #         user = self.query_one("""
    #             SELECT id, username, email, full_name, role, company_id, 
    #                 is_active, is_approved, account_type, created_at, last_login,
    #                 password
    #             FROM users 
    #             WHERE username = ? AND is_active = 1
    #         """, (username_or_email,))
            
    #         # If not found, try email
    #         if not user:
    #             user = self.query_one("""
    #                 SELECT id, username, email, full_name, role, company_id, 
    #                     is_active, is_approved, account_type, created_at, last_login,
    #                     password
    #                 FROM users 
    #                 WHERE email = ? AND is_active = 1
    #             """, (username_or_email,))
            
    #         if not user:
    #             return None
            
    #         stored_password = user.get('password', '')
    #         if not stored_password:
    #             return None
            
    #         # ===== TRY SHA256 FIRST =====
    #         import hashlib
    #         hashed_input = hashlib.sha256(password.encode()).hexdigest()
            
    #         if stored_password == hashed_input:
    #             # Update last login
    #             print(f"❌ updating last login...")
    #             self.execute(
    #                 "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
    #                 (user['id'],)
    #             )
    #             # Remove password before returning
    #             user_copy = dict(user)
    #             del user_copy['password']
    #             return user_copy
            
    #         # ===== TRY BCRYPT AS FALLBACK =====
    #         try:
    #             import bcrypt
    #             # Check if it's a bcrypt hash (starts with $2)
    #             if stored_password.startswith('$2'):
    #                 # Ensure password is bytes for bcrypt
    #                 if isinstance(password, str):
    #                     password_bytes = password.encode('utf-8')
    #                 else:
    #                     password_bytes = password
                    
    #                 if isinstance(stored_password, str):
    #                     stored_hash = stored_password.encode('utf-8')
    #                 else:
    #                     stored_hash = stored_password
                    
    #                 if bcrypt.checkpw(password_bytes, stored_hash):
    #                     # Convert to SHA256 for future use
    #                     new_hash = hashlib.sha256(password.encode()).hexdigest()
    #                     self.execute(
    #                         "UPDATE users SET password = ?, last_login = CURRENT_TIMESTAMP WHERE id = ?",
    #                         (new_hash, user['id'])
    #                     )
    #                     # Remove password before returning
    #                     user_copy = dict(user)
    #                     del user_copy['password']
    #                     return user_copy
    #         except ImportError:
    #             # bcrypt not installed, skip
    #             pass
    #         except Exception as e:
    #             print(f"⚠️ Bcrypt check error: {e}")
            
    #         return None
            
    #     except Exception as e:
    #         print(f"❌ Authentication error: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         return None

    def authenticate_user(self, username_or_email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user - supports both SHA256 and bcrypt hashes
        Works with both SQLite and Supabase
        """
        try:
            # ✅ Use separate queries to avoid parser issues
            # First try username
            user = self.query_one("""
                SELECT id, username, email, full_name, role, company_id, 
                    is_active, is_approved, account_type, created_at, last_login,
                    password
                FROM users 
                WHERE username = ? AND is_active = 1
            """, (username_or_email,))
            
            # If not found, try email
            if not user:
                user = self.query_one("""
                    SELECT id, username, email, full_name, role, company_id, 
                        is_active, is_approved, account_type, created_at, last_login,
                        password
                    FROM users 
                    WHERE email = ? AND is_active = 1
                """, (username_or_email,))
            
            if not user:
                return None
            
            stored_password = user.get('password', '')
            if not stored_password:
                return None
            
            # ===== TRY SHA256 FIRST =====
            import hashlib
            hashed_input = hashlib.sha256(password.encode()).hexdigest()
            
            if stored_password == hashed_input:
                # ✅ Update last login - use direct method based on db type
                self._update_last_login(user['id'])
                
                # Remove password before returning
                user_copy = dict(user)
                del user_copy['password']
                return user_copy
            
            # ===== TRY BCRYPT AS FALLBACK =====
            try:
                import bcrypt
                if stored_password.startswith('$2'):
                    if isinstance(password, str):
                        password_bytes = password.encode('utf-8')
                    else:
                        password_bytes = password
                    
                    if isinstance(stored_password, str):
                        stored_hash = stored_password.encode('utf-8')
                    else:
                        stored_hash = stored_password
                    
                    if bcrypt.checkpw(password_bytes, stored_hash):
                        # Convert to SHA256 for future use
                        new_hash = hashlib.sha256(password.encode()).hexdigest()
                        self._update_user_password_and_login(user['id'], new_hash)
                        
                        user_copy = dict(user)
                        del user_copy['password']
                        return user_copy
            except ImportError:
                pass
            except Exception as e:
                print(f"⚠️ Bcrypt check error: {e}")
            
            return None
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return None


    def _update_last_login(self, user_id: int) -> bool:
        """
        Update user's last_login timestamp - works with both SQLite and Supabase
        """
        try:
            db = self._get_db()
            
            # ✅ If using Supabase, use direct client
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                try:
                    db.supabase.table('users')\
                        .update({'last_login': datetime.now().isoformat()})\
                        .eq('id', user_id)\
                        .execute()
                    print(f"✅ Updated last_login for user {user_id} via Supabase")
                    return True
                except Exception as e:
                    print(f"⚠️ Supabase update error: {e}")
                    # Fall through to execute method
            
            # ✅ Fallback: use execute with string formatting for the ID
            sql = f"UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = {user_id}"
            self.execute(sql)
            return True
            
        except Exception as e:
            print(f"❌ Error updating last_login: {e}")
            return False


    def _update_user_password_and_login(self, user_id: int, new_password_hash: str) -> bool:
        """
        Update user's password and last_login - works with both SQLite and Supabase
        """
        try:
            db = self._get_db()
            
            # ✅ If using Supabase, use direct client
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                try:
                    db.supabase.table('users')\
                        .update({
                            'password': new_password_hash,
                            'last_login': datetime.now().isoformat()
                        })\
                        .eq('id', user_id)\
                        .execute()
                    print(f"✅ Updated password and login for user {user_id} via Supabase")
                    return True
                except Exception as e:
                    print(f"⚠️ Supabase update error: {e}")
                    # Fall through to execute method
            
            # ✅ Fallback: use execute with string formatting
            sql = f"UPDATE users SET password = '{new_password_hash}', last_login = CURRENT_TIMESTAMP WHERE id = {user_id}"
            self.execute(sql)
            return True
            
        except Exception as e:
            print(f"❌ Error updating password and login: {e}")
            return False
    def get_user_by_username_or_email(self, username_or_email: str) -> Optional[Dict]:
        """Get user by username or email - works with both SQLite and Supabase"""
        # ✅ Use separate queries
        user = self.query_one("""
            SELECT id, username, email, full_name, role, company_id,
                is_active, is_approved, account_type, created_at, last_login,
                password
            FROM users
            WHERE username = ? AND is_active = 1
        """, (username_or_email,))
        
        if user:
            return user
        
        user = self.query_one("""
            SELECT id, username, email, full_name, role, company_id,
                is_active, is_approved, account_type, created_at, last_login,
                password
            FROM users
            WHERE email = ? AND is_active = 1
        """, (username_or_email,))
        
        return user
    def create_google_user(self, user_data: Dict) -> Tuple[bool, any]:
        """
        Create a new user from Google OAuth or update existing user.
        
        Returns:
            (success: bool, user_id_or_error: any)
        """
        try:
            print(f"🔍 DatabaseCRUD.create_google_user called")
            print(f"   mode: {self.db_type}")
            
            if self._use_supabase:
                return self._create_google_user_supabase(user_data)
            else:
                return self._create_google_user_sqlite(user_data)
                
        except Exception as e:
            print(f"❌ create_google_user error: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def _create_google_user_supabase(self, user_data: Dict) -> Tuple[bool, any]:
        """Supabase implementation with auto-company creation for individual users"""
        try:
            google_id = user_data.get('google_id', '')
            email = user_data.get('email')
            full_name = user_data.get('full_name', '')
            
            print(f"🔍 _create_google_user_supabase: email={email}")
            
            # Check if user exists by email
            response = self.supabase.table('users')\
                .select('id, auth_provider')\
                .eq('email', email)\
                .execute()
            
            if response.data:
                existing = response.data[0]
                user_id = existing['id']
                print(f"✅ User exists: {user_id}")
                
                # Update with Google info if needed
                if existing.get('auth_provider') != 'google':
                    self.supabase.table('users')\
                        .update({
                            'auth_provider': 'google',
                            'auth_provider_user_id': google_id,
                            'google_id': google_id,
                            'google_email': email,
                            'google_picture': user_data.get('picture', ''),
                            'email_verified': True
                        })\
                        .eq('id', user_id)\
                        .execute()
                    print(f"✅ User {user_id} updated with Google info")
                else:
                    print(f"✅ User {user_id} already has Google auth")
                
                return True, user_id
            
            # Check if username exists
            username = user_data.get('username', email.split('@')[0])
            username_response = self.supabase.table('users')\
                .select('id')\
                .eq('username', username)\
                .execute()
            
            if username_response.data:
                import random
                username = f"{username}_{random.randint(100, 999)}"
                print(f"🔍 Username taken, using: {username}")
            
            # Generate password
            import secrets
            import bcrypt
            temp_password = secrets.token_urlsafe(16)
            hashed = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # ✅ FIXED: Create company for individual user FIRST
            company_name = f"{full_name if full_name else 'Individual'} - Individual"
            
            company_response = self.supabase.table('companies').insert({
                'company_name': company_name,
                'is_individual': True,
                'is_active': True,
                'status': 'active',
                'created_at': datetime.now().isoformat()
            }).execute()
            
            if not company_response.data:
                print(f"❌ Failed to create company for individual user")
                return False, "Failed to create company"
            
            company_id = company_response.data[0].get('id')
            print(f"✅ Company created with ID: {company_id}")
            
            # ✅ FIXED: Create user WITH company_id
            insert_data = {
                'username': username,
                'password': hashed,
                'email': email,
                'full_name': full_name,
                'role': 'individual',
                'account_type': 'individual',
                'company_id': company_id,  # ✅ CRITICAL: Link to company
                'auth_provider': 'google',
                'auth_provider_user_id': google_id,
                'google_id': google_id,
                'google_email': email,
                'google_picture': user_data.get('picture', ''),
                'email_verified': True,
                'is_active': True,
                'is_approved': True
            }
            
            print(f"🔍 Inserting new user with company_id: {company_id}")
            insert_response = self.supabase.table('users').insert(insert_data).execute()
            
            if insert_response.data:
                user_id = insert_response.data[0].get('id')
                print(f"✅ User created with ID: {user_id} and company_id: {company_id}")
                
                # ✅ Create default company profile
                self.supabase.table('company_profile').insert({
                    'company_id': company_id,
                    'legal_name': full_name,
                    'created_at': datetime.now().isoformat()
                }).execute()
                print(f"✅ Company profile created for company {company_id}")
                
                return True, user_id
            else:
                print(f"❌ Insert failed: {insert_response}")
                return False, "Failed to create user in Supabase"
                
        except Exception as e:
            print(f"❌ _create_google_user_supabase error: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)

    def _create_google_user_sqlite(self, user_data: Dict) -> Tuple[bool, any]:
        """SQLite implementation with auto-company creation for individual users"""
        try:
            google_id = user_data.get('google_id', '')
            email = user_data.get('email')
            full_name = user_data.get('full_name', '')
            
            # Check if email exists
            existing = self.query_one(
                "SELECT id, auth_provider FROM users WHERE email = ?",
                (email,)
            )
            
            if existing:
                user_id = existing['id']
                if google_id and existing.get('auth_provider') != 'google':
                    self.execute("""
                        UPDATE users 
                        SET auth_provider = 'google', 
                            google_id = ?, 
                            auth_provider_user_id = ?,
                            google_email = ?,
                            email_verified = 1,
                            google_picture = ?
                        WHERE id = ?
                    """, (google_id, google_id, email, user_data.get('picture', ''), user_id))
                return True, user_id
            
            # Check username
            username = user_data.get('username', email.split('@')[0])
            existing_username = self.query_one(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            )
            if existing_username:
                import random
                username = f"{username}_{random.randint(100, 999)}"
            
            # Generate password
            import secrets
            import bcrypt
            temp_password = secrets.token_urlsafe(16)
            hashed = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # ✅ FIXED: Create company for individual user FIRST
            company_name = f"{full_name if full_name else 'Individual'} - Individual"
            
            self.execute("""
                INSERT INTO companies (company_name, is_individual, is_active, status, created_at)
                VALUES (?, 1, 1, 'active', CURRENT_TIMESTAMP)
            """, (company_name,))
            
            # Get company_id
            company_result = self.query_one(
                "SELECT id FROM companies WHERE company_name = ? ORDER BY id DESC LIMIT 1",
                (company_name,)
            )
            company_id = company_result['id'] if company_result else None
            
            print(f"✅ Company created with ID: {company_id}")
            
            # ✅ FIXED: Create user WITH company_id
            insert_sql = """
                INSERT INTO users (
                    username, password, email, full_name, phone, mobile_number,
                    role, is_active, is_approved, created_at, account_type,
                    auth_provider, google_id, google_email, email_verified,
                    auth_provider_user_id, google_picture, company_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    'individual', 1, 1, CURRENT_TIMESTAMP, 'individual',
                    'google', ?, ?, 1,
                    ?, ?, ?
                )
            """
            
            self.execute(insert_sql, (
                username,
                hashed,
                email,
                full_name,
                user_data.get('phone', ''),
                user_data.get('mobile_number', ''),
                google_id,
                email,
                google_id,
                user_data.get('picture', ''),
                company_id  # ✅ CRITICAL: Link to company
            ))
            
            # Get user_id
            user = self.query_one(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            )
            
            if user:
                user_id = user['id']
                
                # ✅ Create default company profile
                self.execute("""
                    INSERT INTO company_profile (company_id, legal_name, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (company_id, full_name))
                print(f"✅ Company profile created for company {company_id}")
                
                # Insert into user_oauth
                if google_id:
                    try:
                        self.execute("""
                            INSERT INTO user_oauth (user_id, provider_name, provider_user_id, provider_email)
                            VALUES (?, 'google', ?, ?)
                        """, (user_id, google_id, email))
                    except:
                        pass
                return True, user_id
            
            return False, "Failed to create user"
            
        except Exception as e:
            print(f"❌ SQLite error: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)

    
    def create_google_user_bak(self, user_data: Dict) -> tuple:
        """
        Create a new user from Google OAuth (mobile number optional)
        
        Args:
            user_data: Dict with keys: username, email, full_name, google_id, phone (optional)
        
        Returns:
            (success: bool, message: str or user_id: int)
        """
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Validate required fields
            if not user_data.get('username'):
                return False, "Username is required"
            if not user_data.get('email'):
                return False, "Email is required"
            if not user_data.get('full_name'):
                return False, "Full name is required"
            
            # Generate a random password for Google users
            import secrets
            import bcrypt
            temp_password = secrets.token_urlsafe(16)
            hashed = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Check if email already exists
            cursor.execute("SELECT id, auth_provider FROM users WHERE email = ?", (user_data['email'],))
            existing = cursor.fetchone()
            if existing:
                # If user exists, update with Google info if it's a Google user
                user_id = existing[0]
                google_id = user_data.get('google_id')
                if google_id:
                    cursor.execute("""
                        UPDATE users 
                        SET google_id = ?, auth_provider = 'google', email_verified = 1, 
                            auth_provider_user_id = ?
                        WHERE id = ?
                    """, (google_id, google_id, user_id))
                    conn.commit()
                    return True, user_id
                return False, f"Email {user_data['email']} is already registered"
            
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (user_data['username'],))
            if cursor.fetchone():
                return False, f"Username {user_data['username']} is already taken"
            
            # Mobile is optional for Google users
            mobile = user_data.get('mobile_number', '')
            if mobile:
                mobile = self.normalize_mobile(mobile)
                if self.validate_bangladesh_mobile(mobile):
                    cursor.execute("SELECT id FROM users WHERE mobile_number = ?", (mobile,))
                    if cursor.fetchone():
                        return False, f"Mobile number {mobile} is already registered"
                else:
                    mobile = ''
            
            google_id = user_data.get('google_id', '')
            
            # Insert user with OAuth columns
            cursor.execute("""
                INSERT INTO users (
                    username, password, email, full_name, phone, mobile_number,
                    role, is_active, is_approved, created_at, account_type,
                    auth_provider, google_id, google_email, email_verified,
                    auth_provider_user_id, google_picture
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    'individual', 1, 1, CURRENT_TIMESTAMP, 'individual',
                    'google', ?, ?, 1,
                    ?, ?
                )
            """, (
                user_data['username'],
                hashed,
                user_data['email'],
                user_data['full_name'],
                user_data.get('phone', ''),
                mobile,
                google_id,
                user_data['email'],
                google_id,  # auth_provider_user_id
                user_data.get('picture', '')  # google_picture
            ))
            
            user_id = cursor.lastrowid
            
            # Also insert into user_oauth table for extensibility
            if google_id:
                cursor.execute("""
                    INSERT INTO user_oauth (user_id, provider_name, provider_user_id, provider_email)
                    VALUES (?, 'google', ?, ?)
                """, (user_id, google_id, user_data['email']))
            
            conn.commit()
            return True, user_id

    def create_facebook_user(self, user_data: Dict) -> tuple:
        """
        Create a new user from Facebook OAuth (disabled for now)
        
        Args:
            user_data: Dict with keys: username, email, full_name, facebook_id, phone (optional)
        
        Returns:
            (success: bool, message: str or user_id: int)
        """
        # TODO: Implement Facebook OAuth
        logger.warning("Facebook OAuth is not yet implemented")
        return False, "Facebook OAuth is not yet implemented. Please use Google or traditional registration."

    def get_user_by_oauth_provider(self, provider_name: str, provider_user_id: str):
        """Get user by OAuth provider and provider user ID"""
        try:
            # First check user_oauth table
            result = self.query_one("""
                SELECT u.* FROM users u
                JOIN user_oauth o ON u.id = o.user_id
                WHERE o.provider_name = ? AND o.provider_user_id = ?
            """, (provider_name, provider_user_id))
            
            if result:
                return result
            
            # Fallback to direct column check for Google
            if provider_name == 'google':
                result = self.query_one("""
                    SELECT * FROM users WHERE google_id = ?
                """, (provider_user_id,))
                return result
            
            if provider_name == 'facebook':
                result = self.query_one("""
                    SELECT * FROM users WHERE facebook_id = ?
                """, (provider_user_id,))
                return result
            
            return None
        except Exception as e:
            logger.error(f"Error getting user by OAuth provider: {e}")
            return None           
     
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        sql = "SELECT id, username, full_name, email, role FROM users WHERE id = ? AND is_active = 1"
        return self.query_one(sql, (user_id,))
    # # def get_company_subscription(self, company_id: int) -> Dict:
    # #     """Get company's subscription details"""
    # #     try:
    # #         print(f"🔍 get_company_subscription called for company_id: {company_id}")
            
    # #         # First, check if subscription exists
    # #         sub_check = self.query_one("""
    # #             SELECT id, plan, status FROM subscriptions WHERE company_id = ? AND status = 'active'
    # #         """, (company_id,))
            
    # #         print(f"🔍 Subscription check result: {sub_check}")
            
    # #         if not sub_check:
    # #             print(f"⚠️ No active subscription found for company {company_id}")
    # #             return self._get_default_subscription()
            
    # #         # Now get the plan details
    # #         plan_name = sub_check.get('plan', 'free')
    # #         print(f"🔍 Looking for plan: '{plan_name}'")
            
    # #         plan_result = self.query_one("""
    # #             SELECT * FROM subscription_plans WHERE plan_name = ?
    # #         """, (plan_name,))
            
    # #         print(f"🔍 Plan result: {plan_result}")
            
    # #         if plan_result:
    # #             print(f"✅ Found plan: {plan_result.get('plan_name')}")
    # #             # Merge subscription and plan data
    # #             result = dict(sub_check)
    # #             result['max_users'] = plan_result.get('max_users', 1)
    # #             result['extension_auto_fills'] = plan_result.get('extension_auto_fills', 5)
    # #             result['plan_name'] = plan_result.get('plan_name')
    # #             result['monthly_price'] = plan_result.get('monthly_price', 0)
    # #             result['yearly_price'] = plan_result.get('yearly_price', 0)
    # #             result['max_tender_analyses'] = plan_result.get('max_tender_analyses', 5)
    # #             return result
            
    # #         print(f"⚠️ Plan '{plan_name}' not found in subscription_plans")
    # #         return self._get_default_subscription()
            
    # #     except Exception as e:
    # #         print(f"❌ Error in get_company_subscription: {e}")
    # #         import traceback
    # #         traceback.print_exc()
    # #         return self._get_default_subscription()
    # def get_user_subscription(self, user_id: int) -> Dict:
    #     """Get user's subscription details"""
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         # ✅ Try user's own subscription first
    #         cursor.execute("""
    #             SELECT 
    #                 plan as subscription_tier,
    #                 status,
    #                 start_date,
    #                 end_date,
    #                 analyses_limit as max_projects,
    #                 analyses_used,
    #                 max_boq_generations,
    #                 max_bid_optimizations,
    #                 can_export_data,
    #                 can_edit_rates,
    #                 can_delete_rates,
    #                 can_create_versions,
    #                 can_manage_team
    #             FROM subscriptions 
    #             WHERE user_id = ? AND status = 'active'
    #             ORDER BY id DESC
    #             LIMIT 1
    #         """, (user_id,))
            
    #         row = cursor.fetchone()
    #         if row:
    #             return dict(row)
            
    #         # ✅ If no user subscription, check company subscription
    #         cursor.execute("""
    #             SELECT 
    #                 u.company_id,
    #                 s.plan as subscription_tier,
    #                 s.status,
    #                 s.start_date,
    #                 s.end_date,
    #                 s.analyses_limit as max_projects,
    #                 s.analyses_used,
    #                 s.max_boq_generations,
    #                 s.max_bid_optimizations,
    #                 s.can_export_data,
    #                 s.can_edit_rates,
    #                 s.can_delete_rates,
    #                 s.can_create_versions,
    #                 s.can_manage_team
    #             FROM users u
    #             LEFT JOIN subscriptions s ON u.company_id = s.company_id AND s.status = 'active'
    #             WHERE u.id = ?
    #             ORDER BY s.id DESC
    #             LIMIT 1
    #         """, (user_id,))
            
    #         row = cursor.fetchone()
    #         if row and row.get('subscription_tier'):
    #             return dict(row)
            
    #         return {
    #             'subscription_tier': 'free',
    #             'status': 'active',
    #             'max_projects': 5,
    #             'analyses_used': 0,
    #             'max_boq_generations': 5,
    #             'max_bid_optimizations': 5,
    #             'can_export_data': False,
    #             'can_edit_rates': False,
    #             'can_delete_rates': False,
    #             'can_create_versions': False,
    #             'can_manage_team': False
    #         }
    # def get_company_subscription(self, company_id: int) -> Dict:
    #     """Get company's subscription details"""
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         # ✅ Get the latest active subscription ordered by id DESC
    #         cursor.execute("""
    #             SELECT 
    #                 s.plan as subscription_tier,
    #                 s.status,
    #                 s.start_date,
    #                 s.end_date,
    #                 s.analyses_limit as max_projects,
    #                 s.analyses_used,
    #                 s.max_boq_generations,
    #                 s.max_bid_optimizations,
    #                 s.boq_used,
    #                 s.bid_optimizations_used,
    #                 s.can_export_data,
    #                 s.can_edit_rates,
    #                 s.can_delete_rates,
    #                 s.can_create_versions,
    #                 s.can_manage_team,
    #                 s.payment_method,
    #                 s.transaction_id,
    #                 s.updated_at,
    #                 sp.max_users,
    #                 sp.extension_auto_fills,
    #                 sp.plan_name
    #             FROM subscriptions s
    #             LEFT JOIN subscription_plans sp ON s.plan = sp.plan_name
    #             WHERE s.company_id = ? AND s.status = 'active'
    #             ORDER BY s.id DESC
    #             LIMIT 1
    #         """, (company_id,))
            
    #         row = cursor.fetchone()
            
    #         if row:
    #             result = dict(row)
    #             # ✅ Debug print to see what's being returned
    #             print(f"📊 get_company_subscription for company {company_id}: plan={result.get('subscription_tier')}")
    #             return result
            
    #         # ✅ If no active subscription, check if there's any subscription
    #         cursor.execute("""
    #             SELECT 
    #                 plan as subscription_tier,
    #                 status,
    #                 start_date,
    #                 end_date,
    #                 analyses_limit as max_projects,
    #                 analyses_used
    #             FROM subscriptions 
    #             WHERE company_id = ?
    #             ORDER BY id DESC
    #             LIMIT 1
    #         """, (company_id,))
            
    #         row = cursor.fetchone()
    #         if row:
    #             result = dict(row)
    #             print(f"⚠️ Found inactive subscription for company {company_id}: {result.get('subscription_tier')}")
    #             return result
            
    #         print(f"⚠️ No subscription found for company {company_id}")
    #         return {
    #             'subscription_tier': 'free',
    #             'status': 'active',
    #             'max_projects': 5,
    #             'max_users': 1,
    #             'analyses_used': 0,
    #             'max_boq_generations': 5,
    #             'max_bid_optimizations': 5,
    #             'boq_used': 0,
    #             'bid_optimizations_used': 0,
    #             'can_export_data': False,
    #             'can_edit_rates': False,
    #             'can_delete_rates': False,
    #             'can_create_versions': False,
    #             'can_manage_team': False,
    #             'extension_auto_fills': 5
    #         }
    
    # # database/crud_operations.py - Update update_company_subscription

    # def update_company_subscription(self, company_id: int, plan: str, 
    #                                 duration: str = 'monthly', 
    #                                 payment_method: str = 'admin', 
    #                                 transaction_id: str = None) -> bool:
    #     """Update or create subscription for a company"""
    #     from datetime import datetime, timedelta
        
    #     print("\n" + "=" * 60)
    #     print("📝 update_company_subscription() CALLED")
    #     print("=" * 60)
    #     print(f"   company_id: {company_id}")
    #     print(f"   plan: {plan}")
    #     print(f"   duration: {duration}")
    #     print(f"   payment_method: {payment_method}")
    #     print(f"   transaction_id: {transaction_id}")
        
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         start_date = datetime.now().date()
    #         print(f"   start_date: {start_date}")
            
    #         # Plan limits and features
    #         plan_limits = {
    #             'free': {'limit': 5, 'max_boq': 5, 'max_bid': 5},
    #             'basic': {'limit': 30, 'max_boq': 30, 'max_bid': 30},
    #             'professional': {'limit': -1, 'max_boq': 100, 'max_bid': 100},
    #             'enterprise': {'limit': -1, 'max_boq': -1, 'max_bid': -1}
    #         }
            
    #         plan_features = {
    #             'free': {'can_export': 0, 'can_edit_rates': 0, 'can_delete_rates': 0, 
    #                     'can_create_versions': 0, 'can_manage_team': 0},
    #             'basic': {'can_export': 1, 'can_edit_rates': 0, 'can_delete_rates': 0,
    #                     'can_create_versions': 0, 'can_manage_team': 0},
    #             'professional': {'can_export': 1, 'can_edit_rates': 1, 'can_delete_rates': 0,
    #                             'can_create_versions': 1, 'can_manage_team': 1},
    #             'enterprise': {'can_export': 1, 'can_edit_rates': 1, 'can_delete_rates': 1,
    #                         'can_create_versions': 1, 'can_manage_team': 1}
    #         }
            
    #         features = plan_features.get(plan, plan_features['free'])
    #         limits = plan_limits.get(plan, plan_limits['free'])
            
    #         if duration == 'monthly':
    #             end_date = start_date + timedelta(days=30)
    #         else:
    #             end_date = start_date + timedelta(days=365)
    #         print(f"   end_date: {end_date}")
            
    #         trans_id = transaction_id or f"ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
    #         # Check if subscription exists
    #         cursor.execute("""
    #             SELECT id, plan FROM subscriptions 
    #             WHERE company_id = ? AND company_id IS NOT NULL
    #             ORDER BY id DESC LIMIT 1
    #         """, (company_id,))
            
    #         existing = cursor.fetchone()
            
    #         if existing:
    #             print(f"   ✅ Found existing subscription ID: {existing['id']}, Current plan: {existing['plan']}")
                
    #             # UPDATE existing subscription
    #             cursor.execute("""
    #                 UPDATE subscriptions 
    #                 SET plan = ?, 
    #                     status = 'active', 
    #                     start_date = ?, 
    #                     end_date = ?,
    #                     analyses_limit = ?,
    #                     max_boq_generations = ?,
    #                     max_bid_optimizations = ?,
    #                     can_export_data = ?,
    #                     can_edit_rates = ?,
    #                     can_delete_rates = ?,
    #                     can_create_versions = ?,
    #                     can_manage_team = ?,
    #                     payment_method = ?,
    #                     transaction_id = ?,
    #                     updated_at = CURRENT_TIMESTAMP
    #                 WHERE id = ?
    #             """, (
    #                 plan,
    #                 start_date,
    #                 end_date,
    #                 limits['limit'],
    #                 limits['max_boq'],
    #                 limits['max_bid'],
    #                 features['can_export'],
    #                 features['can_edit_rates'],
    #                 features['can_delete_rates'],
    #                 features['can_create_versions'],
    #                 features['can_manage_team'],
    #                 payment_method,
    #                 trans_id,
    #                 existing['id']
    #             ))
    #             print(f"   ✅ Updated subscription ID {existing['id']} to {plan}")
                
    #         else:
    #             print(f"   ⚠️ No existing subscription found, creating new one")
                
    #             # INSERT new subscription
    #             cursor.execute("""
    #                 INSERT INTO subscriptions (
    #                     company_id, plan, status, start_date, end_date,
    #                     analyses_limit, analyses_used,
    #                     max_boq_generations, max_bid_optimizations,
    #                     can_export_data, can_edit_rates, can_delete_rates,
    #                     can_create_versions, can_manage_team,
    #                     payment_method, transaction_id,
    #                     created_at, updated_at
    #                 ) VALUES (?, ?, 'active', ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    #             """, (
    #                 company_id,
    #                 plan,
    #                 start_date,
    #                 end_date,
    #                 limits['limit'],
    #                 limits['max_boq'],
    #                 limits['max_bid'],
    #                 features['can_export'],
    #                 features['can_edit_rates'],
    #                 features['can_delete_rates'],
    #                 features['can_create_versions'],
    #                 features['can_manage_team'],
    #                 payment_method,
    #                 trans_id
    #             ))
    #             print(f"   ✅ Created new subscription for company {company_id} with plan {plan}")
            
    #         # Verify the update worked
    #         print("\n   🔍 Verifying update...")
    #         cursor.execute("""
    #             SELECT id, plan, status, start_date, end_date 
    #             FROM subscriptions 
    #             WHERE company_id = ? AND company_id IS NOT NULL
    #             ORDER BY id DESC LIMIT 1
    #         """, (company_id,))
    #         verify = cursor.fetchone()
    #         if verify:
    #             print(f"   ✅ Verification: Subscription ID {verify['id']} now has plan {verify['plan']}")
    #             return verify['plan'] == plan
            
    #         print("   ✅ Update completed successfully")
    #         return True
    
    # def cancel_user_subscription(self, user_id: int) -> bool:
    #     """Cancel user subscription (set to free)"""
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         cursor.execute("""
    #             UPDATE subscriptions 
    #             SET plan = 'free',
    #                 status = 'active',
    #                 analyses_limit = 5,
    #                 max_boq_generations = 5,
    #                 max_bid_optimizations = 5,
    #                 can_export_data = 0,
    #                 can_edit_rates = 0,
    #                 can_delete_rates = 0,
    #                 can_create_versions = 0,
    #                 can_manage_team = 0,
    #                 updated_at = CURRENT_TIMESTAMP
    #             WHERE user_id = ? AND user_id IS NOT NULL
    #         """, (user_id,))
            
    #         return True
    # def cancel_company_subscription(self, company_id: int) -> bool:
    #     """Cancel subscription for a company (set to free)"""
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         cursor.execute("""
    #             UPDATE subscriptions 
    #             SET plan = 'free',
    #                 status = 'active',
    #                 analyses_limit = 5,
    #                 max_boq_generations = 5,
    #                 max_bid_optimizations = 5,
    #                 can_export_data = 0,
    #                 can_edit_rates = 0,
    #                 can_delete_rates = 0,
    #                 can_create_versions = 0,
    #                 can_manage_team = 0,
    #                 updated_at = CURRENT_TIMESTAMP
    #             WHERE company_id = ?
    #         """, (company_id,))
            
    #         print(f"✅ Cancelled subscription for company {company_id}")
    #         return True

    

    # def update_user_subscription(self, user_id: int, plan: str, 
    #                          duration: str = 'monthly',
    #                          payment_method: str = 'admin',
    #                          transaction_id: str = None) -> bool:
    #     """Update or create subscription for a user"""
    #     from datetime import datetime, timedelta
        
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         start_date = datetime.now().date()
            
    #         # Plan limits
    #         plan_limits = {
    #             'free': {'limit': 5, 'max_boq': 5, 'max_bid': 5},
    #             'basic': {'limit': 30, 'max_boq': 30, 'max_bid': 30},
    #             'professional': {'limit': -1, 'max_boq': 100, 'max_bid': 100},
    #             'enterprise': {'limit': -1, 'max_boq': -1, 'max_bid': -1}
    #         }
            
    #         plan_features = {
    #             'free': {'can_export': 0, 'can_edit_rates': 0, 'can_delete_rates': 0, 
    #                     'can_create_versions': 0, 'can_manage_team': 0},
    #             'basic': {'can_export': 1, 'can_edit_rates': 0, 'can_delete_rates': 0,
    #                     'can_create_versions': 0, 'can_manage_team': 0},
    #             'professional': {'can_export': 1, 'can_edit_rates': 1, 'can_delete_rates': 0,
    #                             'can_create_versions': 1, 'can_manage_team': 1},
    #             'enterprise': {'can_export': 1, 'can_edit_rates': 1, 'can_delete_rates': 1,
    #                         'can_create_versions': 1, 'can_manage_team': 1}
    #         }
            
    #         features = plan_features.get(plan, plan_features['free'])
    #         limits = plan_limits.get(plan, plan_limits['free'])
            
    #         if duration == 'monthly':
    #             end_date = start_date + timedelta(days=30)
    #         else:
    #             end_date = start_date + timedelta(days=365)
            
    #         trans_id = transaction_id or f"USER_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
    #         # Check if subscription exists
    #         cursor.execute('SELECT id FROM subscriptions WHERE user_id = ? AND user_id IS NOT NULL', (user_id,))
    #         existing = cursor.fetchone()
            
    #         if existing:
    #             cursor.execute("""
    #                 UPDATE subscriptions 
    #                 SET plan = ?, 
    #                     status = 'active', 
    #                     start_date = ?, 
    #                     end_date = ?,
    #                     analyses_limit = ?,
    #                     max_boq_generations = ?,
    #                     max_bid_optimizations = ?,
    #                     can_export_data = ?,
    #                     can_edit_rates = ?,
    #                     can_delete_rates = ?,
    #                     can_create_versions = ?,
    #                     can_manage_team = ?,
    #                     payment_method = ?,
    #                     transaction_id = ?,
    #                     updated_at = CURRENT_TIMESTAMP
    #                 WHERE user_id = ?
    #             """, (
    #                 plan, start_date, end_date,
    #                 limits['limit'], limits['max_boq'], limits['max_bid'],
    #                 features['can_export'], features['can_edit_rates'],
    #                 features['can_delete_rates'], features['can_create_versions'],
    #                 features['can_manage_team'],
    #                 payment_method, trans_id, user_id
    #             ))
    #         else:
    #             cursor.execute("""
    #                 INSERT INTO subscriptions (
    #                     user_id, plan, status, start_date, end_date,
    #                     analyses_limit, analyses_used,
    #                     max_boq_generations, max_bid_optimizations,
    #                     can_export_data, can_edit_rates, can_delete_rates,
    #                     can_create_versions, can_manage_team,
    #                     payment_method, transaction_id,
    #                     created_at, updated_at
    #                 ) VALUES (?, ?, 'active', ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    #             """, (
    #                 user_id, plan, start_date, end_date,
    #                 limits['limit'], limits['max_boq'], limits['max_bid'],
    #                 features['can_export'], features['can_edit_rates'],
    #                 features['can_delete_rates'], features['can_create_versions'],
    #                 features['can_manage_team'],
    #                 payment_method, trans_id
    #             ))
            
    #         return True
    # def get_all_users(self, company_id=None, role=None):
    #     """Get all users as dictionaries"""
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         query = '''
    #         SELECT u.id, u.username, u.email, u.full_name, u.phone,
    #             u.mobile_number, u.mobile_verified,  -- ✅ ADD THESE
    #             u.role, u.is_active, u.created_at, u.last_login, 
    #             c.company_name, u.is_approved
    #         FROM users u
    #         JOIN companies c ON u.company_id = c.id
    #         WHERE 1=1
    #         '''
    #         params = []
            
    #         if company_id:
    #             query += " AND u.company_id = ?"
    #             params.append(company_id)
    #         if role:
    #             query += " AND u.role = ?"
    #             params.append(role)
            
    #         query += " ORDER BY u.created_at DESC"
            
    #         cursor.execute(query, params)
    #         rows = cursor.fetchall()
            
    #         # Convert to list of dictionaries
    #         users = []
    #         for row in rows:
    #             users.append({
    #                 'id': row.get('id'),
    #                 'username': row.get('username'),
    #                 'email': row.get('email'),
    #                 'full_name': row.get('full_name'),
    #                 'phone': row.get('phone', ''),
    #                 'mobile_number': row.get('mobile_number', ''),  # ✅ ADDED
    #                 'mobile_verified': row.get('mobile_verified', 0),  # ✅ ADDED
    #                 'role': row.get('role', 'viewer'),
    #                 'is_active': row.get('is_active', 1),
    #                 'created_at': row.get('created_at'),
    #                 'last_login': row.get('last_login'),
    #                 'company_name': row.get('company_name'),
    #                 'is_approved': row.get('is_approved', 1)
    #             })
    #         return users
    
    
    # def _get_default_subscription(self) -> Dict:
    #     """Return default subscription values"""
    #     return {
    #         'id': None,
    #         'plan': 'free',
    #         'subscription_tier': 'free',
    #         'status': 'active',
    #         'start_date': None,
    #         'end_date': None,
    #         'max_projects': 5,
    #         'analyses_used': 0,
    #         'max_boq_generations': 5,
    #         'max_bid_optimizations': 5,
    #         'boq_used': 0,
    #         'bid_optimizations_used': 0,
    #         'can_export_data': False,
    #         'can_edit_rates': False,
    #         'can_delete_rates': False,
    #         'can_create_versions': False,
    #         'can_manage_team': False,
    #         'payment_method': None,
    #         'transaction_id': None,
    #         'updated_at': None,
    #         'max_users': 1,
    #         'extension_auto_fills': 5,
    #         'plan_name': 'free',
    #         'monthly_price': 0,
    #         'yearly_price': 0,
    #         'max_tender_analyses': 5
    #     }
    
    def get_company_stats(self, company_id: int) -> Dict:
        """Get company stats - with proper result handling"""
        try:
            # Get user IDs
            users = self.query("SELECT id FROM users WHERE company_id = ?", (company_id,))
            user_ids = [u['id'] for u in users] if users else []
            
            stats = {
                'total_analyses': 0,
                'avg_confidence': 0,
                'total_users': len(user_ids),
                'win_rate': 0,
                'total_bids': 0,
                'total_wins': 0
            }
            
            if not user_ids:
                return stats
            
            placeholders = ','.join(['?' for _ in user_ids])
            
            # Total analyses
            total_result = self.query_one(f"""
                SELECT COUNT(*) as total FROM tender_analyses
                WHERE user_id IN ({placeholders})
            """, tuple(user_ids))
            stats['total_analyses'] = self._safe_get_value(total_result, 'total', 0)
            
            # Average confidence
            avg_result = self.query_one(f"""
                SELECT AVG(confidence_score) as avg FROM tender_analyses
                WHERE user_id IN ({placeholders}) AND confidence_score IS NOT NULL
            """, tuple(user_ids))
            stats['avg_confidence'] = self._safe_get_value(avg_result, 'avg', 0)
            
            # Total bids (non-null bid_status)
            bids_result = self.query_one(f"""
                SELECT COUNT(*) as total FROM tender_analyses
                WHERE user_id IN ({placeholders}) AND bid_status IS NOT NULL
            """, tuple(user_ids))
            stats['total_bids'] = self._safe_get_value(bids_result, 'total', 0)
            
            # Wins
            wins_result = self.query_one(f"""
                SELECT COUNT(*) as total FROM tender_analyses
                WHERE user_id IN ({placeholders}) AND bid_status = 'won'
            """, tuple(user_ids))
            stats['total_wins'] = self._safe_get_value(wins_result, 'total', 0)
            
            if stats['total_bids'] > 0:
                stats['win_rate'] = (stats['total_wins'] / stats['total_bids']) * 100
            
            return stats
            
        except Exception as e:
            print(f"⚠️ Error getting company stats: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_analyses': 0,
                'avg_confidence': 0,
                'total_users': 0,
                'win_rate': 0,
                'total_bids': 0,
                'total_wins': 0
            }


    def _safe_get_value(self, result, key, default=0):
        """Safely get a value from a query result"""
        if result is None:
            return default
        if isinstance(result, dict):
            return result.get(key, default)
        if isinstance(result, (list, tuple)):
            # If it's a list/tuple, try to get by index or key
            if len(result) > 0:
                if isinstance(result[0], dict):
                    return result[0].get(key, default)
                elif hasattr(result[0], key):
                    return getattr(result[0], key, default)
                elif len(result) > 0:
                    return result[0] if result[0] is not None else default
        if hasattr(result, key):
            return getattr(result, key, default)
        return default


    # ============================================================================
    # COMPANY ANALYTICS QUERIES
    # ============================================================================
    
    def get_company_performance_metrics(self, company_id: int) -> Dict:
        """Get company performance metrics"""
        # Total tenders
        result = self.query_one("""
            SELECT COUNT(*) as count FROM company_tenders 
            WHERE company_id = ? AND is_active = 1
        """, (company_id,))
        total_tenders = result['count'] if result and 'count' in result else 0
        
        # Tenders this month
        start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        result = self.query_one("""
            SELECT COUNT(*) as count FROM company_tenders 
            WHERE company_id = ? AND is_active = 1 AND created_at >= ?
        """, (company_id, start_of_month))
        tenders_this_month = result['count'] if result and 'count' in result else 0
        
        # Win rate
        result = self.query_one("""
            SELECT 
                COUNT(CASE WHEN bid_status = 'won' THEN 1 END) as won,
                COUNT(*) as total
            FROM company_tenders 
            WHERE company_id = ? AND is_active = 1 AND bid_status IN ('won', 'lost')
        """, (company_id,))
        won = result['won'] if result and 'won' in result else 0
        total = result['total'] if result and 'total' in result else 0
        win_rate = (won / total * 100) if total > 0 else 0
        
        # Previous month win rate
        last_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
        result = self.query_one("""
            SELECT 
                COUNT(CASE WHEN bid_status = 'won' THEN 1 END) * 100.0 / COUNT(*) as win_rate
            FROM company_tenders 
            WHERE company_id = ? AND created_at >= ? AND created_at < ?
        """, (company_id, last_month_start, start_of_month))
        prev_win_rate = result['win_rate'] if result and 'win_rate' in result else 0
        
        win_rate_change = win_rate - prev_win_rate
        
        # Total analyses
        result = self.query_one("""
            SELECT COUNT(*) as count FROM tender_analyses 
            WHERE company_id = ?
        """, (company_id,))
        total_analyses = result['count'] if result and 'count' in result else 0
        
        # Analyses this month
        result = self.query_one("""
            SELECT COUNT(*) as count FROM tender_analyses 
            WHERE company_id = ? AND analysis_date >= ?
        """, (company_id, start_of_month))
        analyses_this_month = result['count'] if result and 'count' in result else 0
        
        # Active team members
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        result = self.query_one("""
            SELECT COUNT(DISTINCT u.id) as count
            FROM users u
            WHERE u.company_id = ? AND u.is_active = 1
            AND (u.last_login >= ? OR u.id IN (
                SELECT DISTINCT user_id FROM tender_analyses WHERE analysis_date >= ?
            ))
        """, (company_id, thirty_days_ago, thirty_days_ago))
        active_team = result['count'] if result and 'count' in result else 0
        
        return {
            'total_tenders': total_tenders,
            'tenders_this_month': tenders_this_month,
            'win_rate': win_rate,
            'win_rate_change': win_rate_change,
            'total_analyses': total_analyses,
            'analyses_this_month': analyses_this_month,
            'active_team_members': active_team
        }


    def get_company_ai_metrics(self, company_id: int) -> Dict:
        """Calculate company-specific AI value metrics"""
        # Get total analyses
        result = self.query_one("""
            SELECT COUNT(*) as count FROM tender_analyses WHERE company_id = ?
        """, (company_id,))
        total_analyses = result['count'] if result and 'count' in result else 0
        
        # Get total auto-fills
        result = self.query_one("""
            SELECT COUNT(*) as count FROM extension_auto_fill_log WHERE company_id = ?
        """, (company_id,))
        total_auto_fills = result['count'] if result and 'count' in result else 0
        
        # Average time per tender (PostgreSQL compatible)
        result = self.query_one("""
            SELECT 
                AVG(EXTRACT(EPOCH FROM (analysis_date - created_at))) / 60 as minutes
            FROM tender_analyses ta
            JOIN company_tenders ct ON ta.tender_id = ct.tender_id
            WHERE ta.company_id = ? AND ct.created_at IS NOT NULL
        """, (company_id,))
        avg_time = result['minutes'] if result and 'minutes' in result and result['minutes'] else 45
        
        # Hours saved
        manual_time = 45
        time_saved_per_tender = max(0, manual_time - avg_time)
        hours_saved = (time_saved_per_tender * total_analyses) / 60
        
        # Auto-fill time savings
        auto_fill_hours = (total_auto_fills * 2) / 60
        hours_saved += auto_fill_hours
        
        # Cost savings
        hourly_rate = 500
        cost_savings = hours_saved * hourly_rate
        
        # ROI
        result = self.query_one("""
            SELECT 
                CASE 
                    WHEN plan = 'basic' THEN 4999
                    WHEN plan = 'professional' THEN 14999
                    WHEN plan = 'enterprise' THEN 49999
                    ELSE 0
                END as monthly_cost
            FROM subscriptions 
            WHERE company_id = ? AND status = 'active'
            LIMIT 1
        """, (company_id,))
        monthly_cost = result['monthly_cost'] if result and 'monthly_cost' in result else 4999
        
        annual_cost = monthly_cost * 12
        roi = cost_savings / annual_cost if annual_cost > 0 else 0
        
        return {
            'hours_saved': hours_saved,
            'cost_savings': cost_savings,
            'avg_time_per_tender': avg_time,
            'roi': roi
        }


    def get_bid_optimization_metrics(self, company_id: int) -> Dict:
        """Get bid optimization metrics"""
        # Average recommended bid
        result = self.query_one("""
            SELECT 
                AVG(recommended_bid) as avg_bid,
                AVG(recommended_bid / official_estimate) as avg_ratio
            FROM tender_analyses 
            WHERE company_id = ? AND official_estimate > 0
        """, (company_id,))
        avg_bid = result['avg_bid'] if result and 'avg_bid' in result and result['avg_bid'] else 0
        avg_ratio = (result['avg_ratio'] if result and 'avg_ratio' in result and result['avg_ratio'] else 0) * 100
        
        # Average win probability
        result = self.query_one("""
            SELECT AVG(success_probability) as avg_prob FROM tender_analyses 
            WHERE company_id = ? AND success_probability IS NOT NULL
        """, (company_id,))
        avg_win_prob = (result['avg_prob'] if result and 'avg_prob' in result and result['avg_prob'] else 0) * 100
        
        # Total expected savings
        result = self.query_one("""
            SELECT SUM(official_estimate - recommended_bid) as total_savings
            FROM tender_analyses 
            WHERE company_id = ? AND official_estimate > recommended_bid
        """, (company_id,))
        total_savings = result['total_savings'] if result and 'total_savings' in result and result['total_savings'] else 0
        
        # Bid accuracy
        result = self.query_one("""
            SELECT 
                AVG(100 - ABS(our_bid_amount - winning_bid_amount) / winning_bid_amount * 100) as accuracy
            FROM company_tenders 
            WHERE company_id = ? AND bid_status = 'won' AND winning_bid_amount > 0 AND our_bid_amount > 0
        """, (company_id,))
        accuracy = result['accuracy'] if result and 'accuracy' in result and result['accuracy'] else 0
        
        return {
            'avg_recommended_bid': avg_bid,
            'avg_bid_ratio': avg_ratio,
            'avg_win_probability': avg_win_prob,
            'total_expected_savings': total_savings,
            'bid_accuracy': accuracy
        }


    def get_extension_usage_metrics(self, company_id: int) -> Dict:
        """Get extension usage metrics"""
        # Total auto-fills
        result = self.query_one("""
            SELECT COUNT(*) as count FROM extension_auto_fill_log WHERE company_id = ?
        """, (company_id,))
        total = result['count'] if result and 'count' in result else 0
        
        # Auto-fills this month
        start_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        result = self.query_one("""
            SELECT COUNT(*) as count FROM extension_auto_fill_log 
            WHERE company_id = ? AND filled_at >= ?
        """, (company_id, start_of_month))
        this_month = result['count'] if result and 'count' in result else 0
        
        # Average confidence
        result = self.query_one("""
            SELECT AVG(confidence_score) as avg_conf FROM extension_auto_fill_log 
            WHERE company_id = ? AND confidence_score > 0
        """, (company_id,))
        avg_conf = (result['avg_conf'] if result and 'avg_conf' in result and result['avg_conf'] else 0) * 100
        
        # Get plan limit
        result = self.query_one("""
            SELECT 
                CASE 
                    WHEN plan = 'basic' THEN 5
                    WHEN plan = 'professional' THEN 50
                    WHEN plan = 'enterprise' THEN -1
                    ELSE 5
                END as auto_fill_limit
            FROM subscriptions 
            WHERE company_id = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (company_id,))
        limit = result['auto_fill_limit'] if result and 'auto_fill_limit' in result else 5
        
        # Time saved
        time_saved = (total * 2) / 60
        
        return {
            'total_auto_fills': total,
            'auto_fills_this_month': this_month,
            'avg_confidence': avg_conf,
            'limit': limit,
            'used': this_month,
            'time_saved_auto_fill': time_saved
        }


    def get_tender_status_data(self, company_id: int) -> List[Dict]:
        """Get tender status data for chart"""
        return self.query("""
            SELECT 
                bid_status as status,
                COUNT(*) as count
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1
            GROUP BY bid_status
        """, (company_id,))


    def get_win_rate_trend_data(self, company_id: int) -> List[Dict]:
        """Get win rate trend data"""
        return self.query("""
            SELECT 
                TO_CHAR(created_at, 'YYYY-MM') as month,
                COUNT(CASE WHEN bid_status = 'won' THEN 1 END) * 100.0 / COUNT(*) as win_rate
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1 AND bid_status IN ('won', 'lost')
            GROUP BY TO_CHAR(created_at, 'YYYY-MM')
            ORDER BY month
            LIMIT 12
        """, (company_id,))


    def get_bid_optimization_data(self, company_id: int) -> List[Dict]:
        """Get bid optimization data"""
        return self.query("""
            SELECT 
                ta.official_estimate,
                ta.recommended_bid,
                ct.our_bid_amount as actual_bid
            FROM tender_analyses ta
            LEFT JOIN company_tenders ct ON ta.tender_id = ct.tender_id
            WHERE ta.company_id = ? AND ta.official_estimate > 0
            LIMIT 20
        """, (company_id,))


    def get_team_activity_data(self, company_id: int) -> List[Dict]:
        """Get team activity data"""
        return self.query("""
            SELECT 
                u.full_name,
                COUNT(DISTINCT ta.id) as analyses,
                COUNT(DISTINCT ct.id) as tenders
            FROM users u
            LEFT JOIN tender_analyses ta ON u.id = ta.user_id
            LEFT JOIN company_tenders ct ON u.id = ct.created_by
            WHERE u.company_id = ? AND u.is_active = 1
            GROUP BY u.id
            ORDER BY analyses DESC
            LIMIT 10
        """, (company_id,))


    def get_top_performers_data(self, company_id: int) -> List[Dict]:
        """Get top performers data"""
        return self.query("""
            SELECT 
                u.full_name,
                u.role,
                COUNT(DISTINCT ta.id) as analyses,
                ROUND(AVG(ta.success_probability * 100), 1) as avg_confidence,
                MAX(ta.analysis_date) as last_active
            FROM users u
            LEFT JOIN tender_analyses ta ON u.id = ta.user_id
            WHERE u.company_id = ? AND u.is_active = 1
            GROUP BY u.id
            HAVING analyses > 0
            ORDER BY analyses DESC
            LIMIT 10
        """, (company_id,))


    def get_time_savings_data(self, company_id: int) -> List[Dict]:
        """Get time savings data"""
        return self.query("""
            SELECT 
                TO_CHAR(analysis_date, 'YYYY-MM') as month,
                COUNT(*) * 40 / 60 as hours_saved
            FROM tender_analyses
            WHERE company_id = ?
            GROUP BY TO_CHAR(analysis_date, 'YYYY-MM')
            ORDER BY month
            LIMIT 12
        """, (company_id,))


    def get_extension_usage_data(self, company_id: int) -> List[Dict]:
        """Get extension usage data"""
        return self.query("""
            SELECT 
                TO_CHAR(filled_at, 'YYYY-MM-DD') as date,
                COUNT(*) as fills,
                AVG(confidence_score) * 100 as avg_confidence
            FROM extension_auto_fill_log
            WHERE company_id = ? AND filled_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY TO_CHAR(filled_at, 'YYYY-MM-DD')
            ORDER BY date
        """, (company_id,))


    def get_tender_performance_data(self, company_id: int) -> List[Dict]:
        """Get tender performance data"""
        return self.query("""
            SELECT 
                tender_id,
                tender_title,
                official_estimate,
                our_bid_amount as our_bid,
                winning_bid_amount as winning_bid,
                bid_status as status,
                our_rank,
                total_bidders,
                award_date
            FROM company_tenders
            WHERE company_id = ? AND is_active = 1
            ORDER BY created_at DESC
            LIMIT 20
        """, (company_id,))


    def get_recent_analyses_data(self, company_id: int) -> List[Dict]:
        """Get recent analyses data"""
        return self.query("""
            SELECT 
                tender_title,
                recommended_bid,
                success_probability * 100 as win_probability,
                analysis_date
            FROM tender_analyses
            WHERE company_id = ?
            ORDER BY analysis_date DESC
            LIMIT 10
        """, (company_id,))


    def get_ai_recommendations_data(self, company_id: int) -> Dict:
        """Get data for AI recommendations"""
        # Get low win rate tenders
        result = self.query_one("""
            SELECT COUNT(*) as count FROM company_tenders 
            WHERE company_id = ? AND bid_status = 'lost' AND award_date >= CURRENT_DATE - INTERVAL '90 days'
        """, (company_id,))
        recent_losses = result['count'] if result and 'count' in result else 0
        
        # Get underutilized features
        result = self.query_one("""
            SELECT 
                (SELECT COUNT(*) FROM saved_scenarios WHERE company_id = ?) as scenarios,
                (SELECT COUNT(*) FROM competitor_master WHERE company_id = ?) as competitors
        """, (company_id, company_id))
        scenarios_used = result['scenarios'] if result and 'scenarios' in result else 0
        competitors_added = result['competitors'] if result and 'competitors' in result else 0
        
        return {
            'recent_losses': recent_losses,
            'scenarios_used': scenarios_used,
            'competitors_added': competitors_added
        }
    # database/crud_operations.py - Fixed methods

    def get_user_growth(self, months: int = 6) -> List[Dict]:
        """
        Get user growth data for chart display
        Works with both SQLite and PostgreSQL
        Returns list of dicts with 'month' and 'count' keys
        """
        db = self._get_db()
        
        # Check if users table has data
        try:
            count_result = db.query_one("SELECT COUNT(*) as total FROM users")
            if not count_result or count_result.get('total', 0) == 0:
                return self._get_empty_growth_data(months)
        except Exception as e:
            print(f"Error checking users: {e}")
            return self._get_empty_growth_data(months)
        
        result = []
        
        # Try SQLite first
        try:
            result = db.query("""
                SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
                FROM users
                WHERE created_at IS NOT NULL
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month DESC
                LIMIT ?
            """, (months,))
            
            if result and len(result) > 0:
                if 'month' in result[0] and 'count' in result[0]:
                    return result
        except Exception as e:
            print(f"SQLite query failed: {e}")
        
        # Try PostgreSQL with TO_CHAR
        try:
            result = db.query("""
                SELECT TO_CHAR(created_at, 'YYYY-MM') as month, COUNT(*) as count
                FROM users
                WHERE created_at IS NOT NULL
                GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                ORDER BY month DESC
                LIMIT ?
            """, (months,))
            
            if result and len(result) > 0:
                if 'month' in result[0] and 'count' in result[0]:
                    return result
        except Exception as e:
            print(f"PostgreSQL TO_CHAR query failed: {e}")
        
        # Try PostgreSQL with DATE_TRUNC
        try:
            result = db.query("""
                SELECT DATE_TRUNC('month', created_at)::DATE as month, COUNT(*) as count
                FROM users
                WHERE created_at IS NOT NULL
                GROUP BY DATE_TRUNC('month', created_at)
                ORDER BY month DESC
                LIMIT ?
            """, (months,))
            
            if result and len(result) > 0:
                # Format dates to YYYY-MM
                formatted = []
                for row in result:
                    month_val = row.get('month')
                    if month_val:
                        if hasattr(month_val, 'strftime'):
                            month_str = month_val.strftime('%Y-%m')
                        else:
                            month_str = str(month_val)[:7]
                        formatted.append({
                            'month': month_str,
                            'count': row.get('count', 0)
                        })
                return formatted if formatted else self._get_empty_growth_data(months)
        except Exception as e:
            print(f"PostgreSQL DATE_TRUNC query failed: {e}")
        
        # Try with simple DATE format
        try:
            result = db.query("""
                SELECT DATE(created_at) as registration_date, COUNT(*) as user_count
                FROM users
                WHERE created_at IS NOT NULL
                GROUP BY DATE(created_at)
                ORDER BY registration_date DESC
                LIMIT ?
            """, (months * 3,))
            
            if result and len(result) > 0:
                # Aggregate by month
                monthly_data = {}
                for row in result:
                    date_val = row.get('registration_date')
                    if date_val:
                        month_str = str(date_val)[:7]
                        count = row.get('user_count', 0)
                        monthly_data[month_str] = monthly_data.get(month_str, 0) + count
                
                formatted_result = [
                    {'month': month, 'count': count} 
                    for month, count in sorted(monthly_data.items(), reverse=True)[:months]
                ]
                
                return formatted_result if formatted_result else self._get_empty_growth_data(months)
        except Exception as e:
            print(f"DATE query failed: {e}")
        
        # If all queries fail, return empty data with zero counts
        return self._get_empty_growth_data(months)

    def _get_empty_growth_data(self, months: int) -> List[Dict]:
        """Return empty growth data with zero counts"""
        import datetime
        result = []
        current = datetime.datetime.now()
        
        for i in range(months - 1, -1, -1):
            month_date = current - datetime.timedelta(days=30 * i)
            month_str = month_date.strftime('%Y-%m')
            result.append({
                'month': month_str,
                'count': 0
            })
        
        return result

    def get_extension_download_stats(self) -> Dict:
        """
        Get extension download statistics - NO COMPLEX DATE SQL
        Uses Python for all date filtering
        """
        db = self._get_db()
        
        # Total downloads
        total_downloads = 0
        try:
            total_result = db.query_one("SELECT COUNT(*) as count FROM extension_downloads")
            total_downloads = total_result.get('count', 0) if total_result else 0
        except Exception as e:
            print(f"Error getting total downloads: {e}")
        
        # Daily downloads - Get ALL data, filter in Python
        daily_result = []
        try:
            # Simple query without any date filtering - just get all data
            all_downloads = db.query("""
                SELECT downloaded_at, username 
                FROM extension_downloads 
                ORDER BY downloaded_at DESC
            """)
            
            if all_downloads and len(all_downloads) > 0:
                import datetime
                from collections import defaultdict
                
                now = datetime.datetime.now()
                cutoff = now - datetime.timedelta(days=7)
                daily_counts = defaultdict(int)
                
                for row in all_downloads:
                    downloaded_at = row.get('downloaded_at')
                    if downloaded_at:
                        try:
                            # Parse the date - handle different formats
                            if isinstance(downloaded_at, datetime.datetime):
                                dt = downloaded_at
                            elif isinstance(downloaded_at, str):
                                # Try to parse ISO format
                                try:
                                    dt = datetime.datetime.fromisoformat(downloaded_at.replace('Z', '+00:00'))
                                except:
                                    # Try other formats
                                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                        try:
                                            dt = datetime.datetime.strptime(downloaded_at, fmt)
                                            break
                                        except:
                                            continue
                                    else:
                                        continue
                            else:
                                continue
                            
                            # Check if within last 7 days
                            if dt >= cutoff:
                                day_key = dt.strftime('%Y-%m-%d')
                                daily_counts[day_key] += 1
                        except Exception as e:
                            print(f"Error parsing date {downloaded_at}: {e}")
                            continue
                
                daily_result = [
                    {'day': day, 'count': count} 
                    for day, count in sorted(daily_counts.items(), reverse=True)
                ]
        except Exception as e:
            print(f"Error getting daily downloads: {e}")
        
        # Downloads by user (top 10)
        user_result = []
        try:
            user_result = db.query("""
                SELECT username, COUNT(*) as count
                FROM extension_downloads
                WHERE username IS NOT NULL AND username != ''
                GROUP BY username
                ORDER BY count DESC
                LIMIT 10
            """)
        except Exception as e:
            print(f"Error getting user downloads: {e}")
            # Try without WHERE clause
            try:
                user_result = db.query("""
                    SELECT username, COUNT(*) as count
                    FROM extension_downloads
                    GROUP BY username
                    ORDER BY count DESC
                    LIMIT 10
                """)
            except:
                user_result = []
        
        return {
            'total': total_downloads,
            'daily': daily_result if daily_result else [],
            'by_user': user_result if user_result else []
        }
    
    def get_extension_fill_usage(self, user_id: int, days: int = 30) -> Dict:
        """
        Get extension auto-fill usage statistics
        
        Args:
            user_id: User ID to get usage for
            days: Number of days to look back (default: 30)
        
        Returns:
            Dict: Usage statistics by field type
        """
        db = self._get_db()
        
        try:
            # Get all extension fill logs for the user
            all_logs = db.query("""
                SELECT field_type, used_at 
                FROM extension_fill_log 
                WHERE user_id = ? 
                ORDER BY used_at DESC
            """, (user_id,))
            
            if not all_logs or len(all_logs) == 0:
                return {}
            
            # Filter in Python for date range
            import datetime
            from collections import defaultdict
            
            now = datetime.datetime.now()
            cutoff = now - datetime.timedelta(days=days)
            
            usage_counts = defaultdict(int)
            
            for row in all_logs:
                used_at = row.get('used_at')
                if used_at:
                    try:
                        # Parse the date
                        if isinstance(used_at, datetime.datetime):
                            dt = used_at
                        elif isinstance(used_at, str):
                            # Try different formats
                            try:
                                dt = datetime.datetime.fromisoformat(used_at.replace('Z', '+00:00'))
                            except:
                                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                                    try:
                                        dt = datetime.datetime.strptime(used_at, fmt)
                                        break
                                    except:
                                        continue
                                else:
                                    continue
                        else:
                            continue
                        
                        # Check if within date range
                        if dt >= cutoff:
                            field_type = row.get('field_type', 'unknown')
                            usage_counts[field_type] += 1
                            
                    except Exception as e:
                        print(f"Error parsing date {used_at}: {e}")
                        continue
            
            return dict(usage_counts)
            
        except Exception as e:
            print(f"Error getting extension fill usage: {e}")
            return {}


    def log_extension_fill(self, user_id: int, field_type: str,
                        source_type: str, source_id: int) -> bool:
        """
        Log extension auto-fill usage
        
        Args:
            user_id: User ID
            field_type: Type of field being filled
            source_type: Source of the fill (e.g., 'personnel', 'equipment')
            source_id: ID of the source record
        
        Returns:
            bool: True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            # Insert the log entry
            result = db.execute("""
                INSERT INTO extension_fill_log (user_id, field_type, source_type, source_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, field_type, source_type, source_id))
            
            return result > 0
            
        except Exception as e:
            print(f"Error logging extension fill: {e}")
            return False
    def update_system_config(self, config_key: str, config_value: Dict) -> bool:
        """
        Update or insert system configuration
        
        Args:
            config_key: The configuration key (e.g., 'email_settings', 'security_settings')
            config_value: Dictionary of configuration values
        
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            import json
            import datetime
            
            # Convert config_value to JSON string
            config_json = json.dumps(config_value)
            
            # Check if config exists
            existing = db.query_one("""
                SELECT id FROM system_config WHERE config_key = ?
            """, (config_key,))
            
            if existing:
                # Update existing
                db.execute("""
                    UPDATE system_config 
                    SET config_value = ?, updated_at = ?
                    WHERE config_key = ?
                """, (config_json, datetime.datetime.now().isoformat(), config_key))
            else:
                # Insert new
                db.execute("""
                    INSERT INTO system_config (config_key, config_value, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (config_key, config_json, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
            
            return True
        except Exception as e:
            print(f"Error updating system config '{config_key}': {e}")
            return False


    def get_all_system_configs(self) -> Dict[str, Dict]:
        """
        Get all system configurations
        
        Returns:
            Dictionary with all config keys and their values
        """
        db = self._get_db()
        
        try:
            import json
            results = db.query("""
                SELECT config_key, config_value, updated_at
                FROM system_config 
                ORDER BY config_key
            """)
            
            configs = {}
            for row in results:
                key = row.get('config_key')
                value = row.get('config_value')
                
                # Parse JSON if string
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                
                configs[key] = {
                    'config_value': value,
                    'updated_at': row.get('updated_at')
                }
            
            return configs
        except Exception as e:
            print(f"Error getting all system configs: {e}")
            return {}


    def delete_system_config(self, config_key: str) -> bool:
        """
        Delete system configuration by key
        
        Args:
            config_key: The configuration key to delete
        
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            db.execute("""
                DELETE FROM system_config WHERE config_key = ?
            """, (config_key,))
            return True
        except Exception as e:
            print(f"Error deleting system config '{config_key}': {e}")
            return False


    def get_email_config(self) -> Dict:
        """
        Get email configuration settings
        
        Returns:
            Dictionary with email settings
        """
        config = self.get_system_config('email_settings')
        if config:
            return config.get('config_value', {})
        return {}


    def update_email_config(self, settings: Dict) -> bool:
        """
        Update email configuration settings
        
        Args:
            settings: Dictionary with email settings
        
        Returns:
            True if successful, False otherwise
        """
        return self.update_system_config('email_settings', settings)


    def get_security_config(self) -> Dict:
        """
        Get security configuration settings
        
        Returns:
            Dictionary with security settings
        """
        config = self.get_system_config('security_settings')
        if config:
            return config.get('config_value', {})
        return {}


    def update_security_config(self, settings: Dict) -> bool:
        """
        Update security configuration settings
        
        Args:
            settings: Dictionary with security settings
        
        Returns:
            True if successful, False otherwise
        """
        return self.update_system_config('security_settings', settings)


    def get_system_config_settings(self) -> Dict:
        """
        Get system configuration settings
        
        Returns:
            Dictionary with system settings
        """
        config = self.get_system_config('system_settings')
        if config:
            return config.get('config_value', {})
        return {}


    def update_system_config_settings(self, settings: Dict) -> bool:
        """
        Update system configuration settings
        
        Args:
            settings: Dictionary with system settings
        
        Returns:
            True if successful, False otherwise
        """
        return self.update_system_config('system_settings', settings)


    def get_performance_config(self) -> Dict:
        """
        Get performance configuration settings
        
        Returns:
            Dictionary with performance settings
        """
        config = self.get_system_config('performance_settings')
        if config:
            return config.get('config_value', {})
        return {}


    def update_performance_config(self, settings: Dict) -> bool:
        """
        Update performance configuration settings
        
        Args:
            settings: Dictionary with performance settings
        
        Returns:
            True if successful, False otherwise
        """
        return self.update_system_config('performance_settings', settings)


    def get_maintenance_mode(self) -> bool:
        """
        Check if maintenance mode is enabled
        
        Returns:
            True if maintenance mode is enabled, False otherwise
        """
        settings = self.get_system_config_settings()
        return settings.get('enable_maintenance_mode', False)


    def set_maintenance_mode(self, enabled: bool) -> bool:
        """
        Set maintenance mode
        
        Args:
            enabled: True to enable, False to disable
        
        Returns:
            True if successful, False otherwise
        """
        settings = self.get_system_config_settings()
        settings['enable_maintenance_mode'] = enabled
        return self.update_system_config_settings(settings)


    def get_registration_status(self) -> bool:
        """
        Check if registration is enabled
        
        Returns:
            True if registration is enabled, False otherwise
        """
        settings = self.get_system_config_settings()
        return settings.get('enable_registration', True)


    def set_registration_status(self, enabled: bool) -> bool:
        """
        Set registration status
        
        Args:
            enabled: True to enable, False to disable
        
        Returns:
            True if successful, False otherwise
        """
        settings = self.get_system_config_settings()
        settings['enable_registration'] = enabled
        return self.update_system_config_settings(settings)


    def clear_system_cache(self) -> bool:
        """
        Clear system cache
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # You can add cache clearing logic here
            # For example, clear any cached queries, session data, etc.
            
            # If you have a cache dictionary, clear it
            if hasattr(self, '_cache'):
                self._cache = {}
            
            # If you have Redis or other cache, clear it here
            # redis_client.flushdb() etc.
            
            return True
        except Exception as e:
            print(f"Error clearing system cache: {e}")
            return False


    def init_system_config_table(self) -> bool:
        """
        Initialize system_config table if it doesn't exist
        
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            # Check if table exists
            result = db.query_one("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='system_config'
            """)
            
            if not result:
                # Create table
                db.execute("""
                    CREATE TABLE IF NOT EXISTS system_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_key TEXT UNIQUE NOT NULL,
                        config_value TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
                
                # Insert default configurations
                import json
                import datetime
                
                defaults = {
                    'email_settings': {
                        'smtp_host': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'smtp_user': '',
                        'smtp_password': '',
                        'from_email': '',
                        'from_name': 'TenderAI'
                    },
                    'security_settings': {
                        'require_2fa': False,
                        'session_timeout': 30,
                        'max_login_attempts': 5,
                        'password_policy': 'strong',
                        'enable_ssl': True,
                        'force_https': True
                    },
                    'system_settings': {
                        'enable_maintenance_mode': False,
                        'enable_registration': True,
                        'enable_analytics': True,
                        'default_language': 'en',
                        'timezone': 'UTC',
                        'date_format': 'YYYY-MM-DD',
                        'enable_audit_log': True
                    },
                    'performance_settings': {
                        'cache_enabled': True,
                        'cache_duration': 300,
                        'max_query_limit': 1000,
                        'enable_query_logging': True,
                        'enable_api_caching': True,
                        'compression_enabled': True
                    }
                }
                
                now = datetime.datetime.now().isoformat()
                for key, value in defaults.items():
                    db.execute("""
                        INSERT INTO system_config (config_key, config_value, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (key, json.dumps(value), now, now))
                
                print("System config table initialized with defaults")
            
            return True
        except Exception as e:
            print(f"Error initializing system config table: {e}")
            return False

# =============================================================================
# SYSTEM CONFIGURATION METHODS (Supabase compatible)
# =============================================================================

    def get_system_config(self, config_key: str) -> Optional[Dict]:
        """
        Get system configuration by key.
        
        Args:
            config_key: The configuration key (e.g., 'email_settings', 'security_settings')
        
        Returns:
            Dictionary with config data or None if not found
        """
        db = self._get_db()
        
        try:
            # Table has: key, value, updated_at, updated_by
            result = db.query_one("""
                SELECT key, value, updated_at, updated_by
                FROM system_config 
                WHERE key = ?
            """, (config_key,))
            
            if result:
                # Parse JSON if value is a string
                if isinstance(result.get('value'), str):
                    try:
                        import json
                        result['value'] = json.loads(result['value'])
                    except:
                        pass
                
                # Map to expected format for backward compatibility
                return {
                    'config_key': result.get('key'),
                    'config_value': result.get('value'),
                    'updated_at': result.get('updated_at'),
                    'updated_by': result.get('updated_by')
                }
            return None
        except Exception as e:
            print(f"Error getting system config '{config_key}': {e}")
            return None


    def update_system_config(self, config_key: str, config_value: Dict) -> bool:
        """
        Update or insert system configuration.
        
        Args:
            config_key: The configuration key (e.g., 'email_settings', 'security_settings')
            config_value: Dictionary of configuration values
        
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            import json
            import datetime
            
            value_json = json.dumps(config_value)
            now = datetime.datetime.now().isoformat()
            user_id = st.session_state.get('user_id') if hasattr(st, 'session_state') else None
            
            # Check if config exists
            existing = db.query_one("""
                SELECT key FROM system_config WHERE key = ?
            """, (config_key,))
            
            if existing:
                db.execute("""
                    UPDATE system_config 
                    SET value = ?, updated_at = ?, updated_by = ?
                    WHERE key = ?
                """, (value_json, now, user_id, config_key))
            else:
                db.execute("""
                    INSERT INTO system_config (key, value, updated_at, updated_by)
                    VALUES (?, ?, ?, ?)
                """, (config_key, value_json, now, user_id))
            
            return True
        except Exception as e:
            print(f"Error updating system config '{config_key}': {e}")
            return False


    def get_all_system_configs(self) -> Dict[str, Dict]:
        """
        Get all system configurations.
        
        Returns:
            Dictionary with all config keys and their values
        """
        db = self._get_db()
        
        try:
            import json
            results = db.query("""
                SELECT key, value, updated_at, updated_by
                FROM system_config 
                ORDER BY key
            """)
            
            configs = {}
            for row in results:
                key = row.get('key')
                value = row.get('value')
                
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                
                configs[key] = {
                    'config_value': value,
                    'updated_at': row.get('updated_at'),
                    'updated_by': row.get('updated_by')
                }
            
            return configs
        except Exception as e:
            print(f"Error getting all system configs: {e}")
            return {}


    def delete_system_config(self, config_key: str) -> bool:
        """Delete system configuration by key."""
        db = self._get_db()
        
        try:
            db.execute("""
                DELETE FROM system_config WHERE key = ?
            """, (config_key,))
            return True
        except Exception as e:
            print(f"Error deleting system config '{config_key}': {e}")
            return False


    # =============================================================================
    # COMPANY CONFIGURATION METHODS
    # =============================================================================

    def get_company_config(self, company_id: int, config_key: str) -> Optional[Any]:
        """
        Get company-specific configuration.
        
        Args:
            company_id: Company ID
            config_key: Configuration key
        
        Returns:
            Configuration value or None if not found
        """
        db = self._get_db()
        
        try:
            # Check if company_settings table exists with key/value columns
            result = db.query_one("""
                SELECT value FROM company_settings 
                WHERE company_id = ? AND key = ?
            """, (company_id, config_key))
            
            if result:
                value = result.get('value')
                if isinstance(value, str):
                    try:
                        import json
                        return json.loads(value)
                    except:
                        return value
                return value
            
            # If not found, try to get from company attributes
            company = self.get_company_by_id(company_id)
            if company and config_key in company:
                return company.get(config_key)
            
            return None
        except Exception as e:
            print(f"Error getting company config {company_id}:{config_key}: {e}")
            return None


    def set_company_config(self, company_id: int, config_key: str, config_value: Any,
                        description: str = None, user_id: int = None) -> bool:
        """
        Set company-specific configuration.
        
        Args:
            company_id: Company ID
            config_key: Configuration key
            config_value: Configuration value
            description: Optional description
            user_id: Optional user ID who made the change
        
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            import json
            import datetime
            
            # Convert to JSON if it's a dict or list
            if isinstance(config_value, (dict, list)):
                value_json = json.dumps(config_value)
            else:
                value_json = str(config_value)
            
            now = datetime.datetime.now().isoformat()
            
            # Check if exists
            existing = db.query_one("""
                SELECT id FROM company_settings 
                WHERE company_id = ? AND key = ?
            """, (company_id, config_key))
            
            if existing:
                db.execute("""
                    UPDATE company_settings 
                    SET value = ?, description = ?, updated_at = ?, updated_by = ?
                    WHERE company_id = ? AND key = ?
                """, (value_json, description, now, user_id, company_id, config_key))
            else:
                db.execute("""
                    INSERT INTO company_settings 
                    (company_id, key, value, description, created_at, updated_at, created_by, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (company_id, config_key, value_json, description, now, now, user_id, user_id))
            
            return True
        except Exception as e:
            print(f"Error setting company config {company_id}:{config_key}: {e}")
            return False


    def get_all_company_configs(self, company_id: int) -> Dict[str, Any]:
        """
        Get all company-specific configurations.
        
        Args:
            company_id: Company ID
        
        Returns:
            Dictionary of all company configs
        """
        db = self._get_db()
        
        try:
            import json
            configs = {}
            
            # Get from company_settings table
            results = db.query("""
                SELECT key, value, description, updated_at
                FROM company_settings 
                WHERE company_id = ?
            """, (company_id,))
            
            for row in results:
                key = row.get('key')
                value = row.get('value')
                
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                
                configs[key] = {
                    'config_value': value,
                    'description': row.get('description'),
                    'updated_at': row.get('updated_at')
                }
            
            # Also get from company attributes
            company = self.get_company_by_id(company_id)
            if company:
                for key, value in company.items():
                    if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']:
                        if key not in configs:
                            configs[key] = {
                                'config_value': value,
                                'description': 'Company attribute',
                                'updated_at': company.get('updated_at')
                            }
            
            return configs
        except Exception as e:
            print(f"Error getting all company configs for {company_id}: {e}")
            return {}


    def delete_company_config(self, company_id: int, config_key: str) -> bool:
        """Delete company-specific configuration."""
        db = self._get_db()
        
        try:
            db.execute("""
                DELETE FROM company_settings 
                WHERE company_id = ? AND key = ?
            """, (company_id, config_key))
            return True
        except Exception as e:
            print(f"Error deleting company config {company_id}:{config_key}: {e}")
            return False


    # =============================================================================
    # COMPANY SETTINGS SHORTCUT METHODS
    # =============================================================================

    def get_company_setting(self, company_id: int, setting_key: str, default: Any = None) -> Any:
        """
        Get a company setting with default fallback.
        
        Args:
            company_id: Company ID
            setting_key: Setting key
            default: Default value if not found
        
        Returns:
            Setting value or default
        """
        value = self.get_company_config(company_id, setting_key)
        return value if value is not None else default


    def update_company_setting(self, company_id: int, setting_key: str, 
                            setting_value: Any, user_id: int = None) -> bool:
        """
        Update a company setting.
        
        Args:
            company_id: Company ID
            setting_key: Setting key
            setting_value: Setting value
            user_id: Optional user ID
        
        Returns:
            True if successful, False otherwise
        """
        return self.set_company_config(company_id, setting_key, setting_value, user_id=user_id)


    def get_company_settings_batch(self, company_id: int, setting_keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple company settings at once.
        
        Args:
            company_id: Company ID
            setting_keys: List of setting keys
        
        Returns:
            Dictionary of setting key-value pairs
        """
        db = self._get_db()
        
        try:
            import json
            placeholders = ','.join(['?'] * len(setting_keys))
            results = db.query(f"""
                SELECT key, value FROM company_settings 
                WHERE company_id = ? AND key IN ({placeholders})
            """, (company_id, *setting_keys))
            
            settings = {}
            for row in results:
                key = row.get('key')
                value = row.get('value')
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                settings[key] = value
            
            return settings
        except Exception as e:
            print(f"Error getting company settings batch: {e}")
            return {}


    # =============================================================================
    # COMPANY ATTRIBUTE HELPERS
    # =============================================================================

    def get_company_attribute(self, company_id: int, attr_name: str, default: Any = None) -> Any:
        """
        Get a company attribute directly.
        
        Args:
            company_id: Company ID
            attr_name: Attribute name
            default: Default value if not found
        
        Returns:
            Attribute value or default
        """
        company = self.get_company_by_id(company_id)
        if company:
            return company.get(attr_name, default)
        return default


    def update_company_attribute(self, company_id: int, attr_name: str, attr_value: Any) -> bool:
        """
        Update a company attribute directly.
        
        Args:
            company_id: Company ID
            attr_name: Attribute name
            attr_value: Attribute value
        
        Returns:
            True if successful, False otherwise
        """
        return self.update_company(company_id, **{attr_name: attr_value})


    # =============================================================================
    # CONFIGURATION INITIALIZATION
    # =============================================================================

    def init_system_config_table(self) -> bool:
        """
        Initialize system_config table with default values if it doesn't exist.
        
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        
        try:
            import json
            import datetime
            
            # Check if table exists
            result = db.query_one("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'system_config'
            """)
            
            if not result:
                # Create table with correct column names
                db.execute("""
                    CREATE TABLE system_config (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_by INTEGER
                    )
                """)
                
                # Create company_settings table
                db.execute("""
                    CREATE TABLE company_settings (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by INTEGER,
                        updated_by INTEGER,
                        UNIQUE(company_id, key)
                    )
                """)
                
                # Insert default configurations
                now = datetime.datetime.now().isoformat()
                defaults = {
                    'email_settings': {
                        'smtp_host': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'smtp_user': '',
                        'smtp_password': '',
                        'from_email': '',
                        'from_name': 'TenderAI'
                    },
                    'security_settings': {
                        'require_2fa': False,
                        'session_timeout': 30,
                        'max_login_attempts': 5,
                        'password_policy': 'strong',
                        'enable_ssl': True,
                        'force_https': True
                    },
                    'system_settings': {
                        'enable_maintenance_mode': False,
                        'enable_registration': True,
                        'enable_analytics': True,
                        'default_language': 'en',
                        'timezone': 'UTC',
                        'date_format': 'YYYY-MM-DD',
                        'enable_audit_log': True
                    },
                    'performance_settings': {
                        'cache_enabled': True,
                        'cache_duration': 300,
                        'max_query_limit': 1000,
                        'enable_query_logging': True,
                        'enable_api_caching': True,
                        'compression_enabled': True
                    }
                }
                
                for key, value in defaults.items():
                    db.execute("""
                        INSERT INTO system_config (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, json.dumps(value), now))
                
                print("System config tables initialized with defaults")
            else:
                # Check if table has correct columns
                columns = db.query("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'system_config'
                """)
                
                column_names = [c.get('column_name') for c in columns]
                
                # If table exists but has wrong columns, try to migrate
                if 'key' not in column_names or 'value' not in column_names:
                    print("Warning: system_config table has wrong column names. Expected: key, value")
                    print(f"Current columns: {column_names}")
                    # You might want to handle migration here
            
            return True
        except Exception as e:
            print(f"Error initializing system config table: {e}")
            return False
    def get_active_version(self, source=None) -> List[Dict]:
        """Get active version for a source or all active versions"""
        db = self._get_db()
        
        if source:
            results = db.query("""
                SELECT * FROM rate_versions 
                WHERE source = ? AND is_active = 1
                ORDER BY edition_year DESC
                LIMIT 1
            """, (source,))
        else:
            results = db.query("""
                SELECT * FROM rate_versions 
                WHERE is_active = 1
                ORDER BY source, edition_year DESC
            """)
        
        # ✅ Ensure each row is a dict
        return [dict(row) for row in results] if results else []