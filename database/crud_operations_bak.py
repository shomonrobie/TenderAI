# database/crud_operations.py
import streamlit as st
import sqlite3
import json
import logging
import hashlib
import secrets
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager
import bcrypt
import pandas as pd
from database.connection import db_connection
import re

logger = logging.getLogger(__name__)

class DatabaseCRUD:
    """Handles all database CRUD operations"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path  # Kept for compatibility, but not used directly
        self.db_conn = db_connection
    
    def get_connection(self):
        """
        Returns raw database connection (works with BOTH patterns)
        - Direct: conn = db.get_connection()
        - Context: with db.get_connection() as conn:
        """
        return self.db_conn._connect_func()
    
    def get_db_type(self):
        """Get current database type"""
        return self.db_conn.db_type
    
    def _row_to_dict(self, row, cursor):
        """Convert database row to dictionary (works for all databases)"""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))

    def execute(self, sql: str, params: tuple = None) -> int:
        """Execute SQL with parameter substitution"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.rowcount
    
    def query(self, sql: str, params: tuple = None):
        """Execute query and return results as list of dicts"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Convert to dict based on database type
            if self.get_db_type() in ['postgresql', 'cockroachdb']:
                # Already dict from RealDictCursor
                return [dict(row) for row in cursor.fetchall()]
            else:
                # SQLite or MySQL - need manual conversion
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
    
    def query_one(self, sql: str, params: tuple = None):
        """Execute query and return single result as dict"""
        results = self.query(sql, params)
        return results[0] if results else None
    
    # ==================== DATABASE-AGNOSTIC SCHEMA METHODS ====================
    
    def get_existing_tables(self):
        """Get list of existing tables (database-agnostic)"""
        db_type = self.get_db_type()
        
        if db_type == 'sqlite':
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        elif db_type in ['postgresql', 'cockroachdb']:
            sql = """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        elif db_type == 'mysql':
            sql = "SHOW TABLES"
        else:
            return set()
        
        results = self.query(sql)
        if db_type == 'mysql':
            # MySQL returns dict with key like 'Tables_in_database'
            return {list(row.values())[0] for row in results}
        return {row['name'] if 'name' in row else list(row.values())[0] for row in results}
    
    def get_table_columns(self, table_name: str):
        """Get table columns (database-agnostic)"""
        db_type = self.get_db_type()
        
        if db_type == 'sqlite':
            sql = f"PRAGMA table_info({table_name})"
            results = self.query(sql)
            return {row['name']: {
                'type': row['type'],
                'notnull': bool(row['notnull']),
                'default': row['dflt_value'],
                'pk': bool(row['pk'])
            } for row in results}
        
        elif db_type in ['postgresql', 'cockroachdb']:
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
        db_type = self.get_db_type()
        
        if db_type == 'sqlite':
            sql = "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            results = self.query(sql)
            return {row['name']: row['tbl_name'] for row in results}
        
        elif db_type in ['postgresql', 'cockroachdb']:
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
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            db_type = self.get_db_type()
            
            if db_type == 'sqlite':
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            elif db_type in ['postgresql', 'cockroachdb']:
                sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
            elif db_type == 'mysql':
                sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
            else:
                return False
            
            cursor.execute(sql)
            return True
    # ==================== HELPER METHODS ====================
    
    def validate_bangladesh_mobile(self, mobile: str) -> bool:
        """Validate Bangladeshi mobile number"""
        if not mobile:
            return False
        mobile = re.sub(r'[\s\-+]', '', mobile)
        if mobile.startswith('88'):
            mobile = mobile[2:]
        pattern = r'^01[3-9]\d{8}$'
        return bool(re.match(pattern, mobile))
    
    def normalize_mobile(self, mobile: str) -> str:
        """Normalize mobile number to standard format"""
        if not mobile:
            return mobile
        mobile = re.sub(r'[\s\-+]', '', mobile)
        if mobile.startswith('+88'):
            mobile = mobile[3:]
        elif mobile.startswith('88'):
            mobile = mobile[2:]
        return mobile

    # ==================== USER METHODS ====================

    def create_user(self, username: str, email: str, mobile_number: str,
                   password: str, full_name: str = None, role: str = 'user',
                   company_id: int = None) -> Optional[int]:
        """Create a new user with unique mobile number"""
        
        # Validate mobile
        mobile_number = self.normalize_mobile(mobile_number)
        if not self.validate_bangladesh_mobile(mobile_number):
            raise ValueError(f"Invalid mobile number: {mobile_number}")
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Check uniqueness
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                raise ValueError(f"Username {username} already exists")
            
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                raise ValueError(f"Email {email} already exists")
            
            cursor.execute("SELECT id FROM users WHERE mobile_number = ?", (mobile_number,))
            if cursor.fetchone():
                raise ValueError(f"Mobile number {mobile_number} is already registered")
            
            # Hash password with bcrypt
            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            cursor.execute("""
                INSERT INTO users 
                (username, email, mobile_number, password, full_name, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (username, email, mobile_number, hashed_password, full_name, role, company_id))
            
            return cursor.lastrowid
        

    def authenticate_user(self, username_or_email: str, password: str) -> Optional[Dict]:
        """Authenticate user - returns DICT"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            cursor.execute("""
                SELECT id, username, email, full_name, role, company_id, 
                    is_active, is_approved, account_type, created_at, last_login,
                    password
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            """, (username_or_email, username_or_email))
            
            row = cursor.fetchone()
            
            if row:
                # Convert to dict if it's a tuple
                if isinstance(row, dict):
                    user_dict = row
                else:
                    # Get column names from cursor description
                    columns = [description[0] for description in cursor.description]
                    user_dict = dict(zip(columns, row))
                
                # Now user_dict is always a dictionary
                if bcrypt.checkpw(password.encode(), user_dict['password'].encode()):
                    # Update last login
                    cursor.execute(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                        (user_dict['id'],)
                    )
                    conn.commit()
                    del user_dict['password']
                    return user_dict
            
            return None

    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID (without password)"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, username, email, mobile_number, full_name, role, 
                       company_id, is_active, created_at, last_login,
                       mobile_verified, email_verified
                FROM users 
                WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_mobile(self, mobile_number: str) -> Optional[Dict]:
        """Get user by mobile number"""
        mobile_number = self.normalize_mobile(mobile_number)
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, username, email, mobile_number, full_name, role, 
                       company_id, is_active, created_at, last_login,
                       mobile_verified, email_verified
                FROM users 
                WHERE mobile_number = ?
            """, (mobile_number,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_user_verification(self, user_id: int, contact_type: str, verified: bool = True) -> bool:
        """Update user verification status"""
        field = f"{contact_type}_verified"
        time_field = f"{contact_type}_verified_at"
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                UPDATE users
                SET {field} = ?, {time_field} = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (1 if verified else 0, user_id))
            
            return cursor.rowcount > 0
    
    # database/crud_operations.py - Add this method

    
    # database/crud_operations.py - Fixed get_all_users

    def get_all_users(self, company_id=None, role=None):
        """Get all users as dictionaries"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = '''
            SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                u.created_at, u.last_login, c.company_name, u.is_approved
            FROM users u
            JOIN companies c ON u.company_id = c.id
            WHERE 1=1
            '''
            params = []
            
            if company_id:
                query += " AND u.company_id = ?"
                params.append(company_id)
            if role:
                query += " AND u.role = ?"
                params.append(role)
            
            query += " ORDER BY u.created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries using dict keys
            users = []
            for row in rows:
                # row is now a dict-like object
                users.append({
                    'id': row.get('id'),
                    'username': row.get('username'),
                    'email': row.get('email'),
                    'full_name': row.get('full_name'),
                    'phone': row.get('phone', ''),
                    'role': row.get('role', 'viewer'),
                    'is_active': row.get('is_active', 1),
                    'created_at': row.get('created_at'),
                    'last_login': row.get('last_login'),
                    'company_name': row.get('company_name'),
                    'is_approved': row.get('is_approved', 1)
                })
            return users

    def get_all_users_filtered(self, company_id=None, search="", role="", status=None, limit=20, offset=0):
        """Get users filtered by company, search, role, status"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Build base query
            if company_id == -1:
                # Special case: get system users only (company_id IS NULL)
                query = """
                    SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                        u.created_at, u.last_login, NULL as company_name, u.is_approved
                    FROM users u
                    WHERE u.company_id IS NULL
                """
                params = []
            elif company_id and company_id > 0:
                # Get users for a specific company
                query = """
                    SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                        u.created_at, u.last_login, c.company_name, u.is_approved
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    WHERE u.company_id = ?
                """
                params = [company_id]
            else:
                # Get all users (including system users) - for system admin
                query = """
                    SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                        u.created_at, u.last_login, c.company_name, u.is_approved
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    WHERE 1=1
                """
                params = []
            
            # Add search filter
            if search:
                query += " AND (u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            
            # Add role filter
            if role:
                query += " AND u.role = ?"
                params.append(role)
            
            # Add status filter
            if status is not None:
                query += " AND u.is_active = ?"
                params.append(1 if status else 0)
            
            # Create count query
            count_query = query.replace(
                "SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, u.created_at, u.last_login, c.company_name, u.is_approved",
                "SELECT COUNT(*)"
            )
            
            # Execute count query
            try:
                cursor.execute(count_query, params)
                count_result = cursor.fetchone()
                # FIX: Use dict key access instead of index
                total = count_result.get('COUNT(*)', 0) if count_result else 0
            except Exception as e:
                print(f"Count query error: {e}")
                total = 0
            
            # Add pagination
            query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute main query
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            except Exception as e:
                print(f"Main query error: {e}")
                rows = []
            
            # Convert to list of dicts
            users = []
            for row in rows:
                users.append({
                    'id': row.get('id'),
                    'username': row.get('username'),
                    'email': row.get('email'),
                    'full_name': row.get('full_name'),
                    'phone': row.get('phone', ''),
                    'role': row.get('role', 'viewer'),
                    'is_active': row.get('is_active', 1),
                    'created_at': row.get('created_at'),
                    'last_login': row.get('last_login'),
                    'company_name': row.get('company_name'),
                    'is_approved': row.get('is_approved', 1)
                })
            
            return users, total
    # ==================== SYSTEM CONFIG METHODS ====================
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get system configuration value"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                value = row['value']
                # Parse boolean
                if value.lower() == 'true':
                    return True
                elif value.lower() == 'false':
                    return False
                return value
            
            return default
    
    def set_config(self, key: str, value: Any, updated_by: int = None) -> bool:
        """Set system configuration value"""
        # Convert boolean to string
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        else:
            value = str(value)
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_by, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value, updated_by))
            
            return True
    


    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information"""
        # Remove subscription_tier from allowed fields since it doesn't exist
        allowed_fields = ['email', 'full_name', 'role', 'company_id', 'is_active']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(user_id)
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0


    
    def delete_user(self, user_id: int, hard_delete: bool = False) -> bool:
        """Delete or deactivate user"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if hard_delete:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            else:
                cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
            
            return cursor.rowcount > 0
    
    def reset_password(self, user_id: int, new_password: str) -> bool:
        """Reset user password using bcrypt"""
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", 
                        (hashed, user_id))
            return cursor.rowcount > 0

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, username, email, full_name, role, company_id, is_active,
                    created_at, last_login
                FROM users WHERE email = ?
            """, (email,))
            
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== QUERY METHODS ====================
    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query and return results as list of dicts"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    
    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """Execute SELECT query and return single result as dict"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def execute(self, sql: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return rowcount"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.rowcount
    
    @property
    def last_insert_id(self) -> int:
        """Get last inserted row ID"""
        with self.get_connection() as conn:
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ==================== SUBSCRIPTION METHODS ====================
    
    # Fix subscription methods to use subscriptions table instead of users table
    def get_user_subscription(self, user_id: int) -> Dict:
        """Get user's subscription details from subscriptions table"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT plan as subscription_tier, status, start_date, end_date,
                    analyses_used as api_calls_used, analyses_limit as api_calls_limit,
                    max_boq_generations, max_bid_optimizations
                FROM subscriptions 
                WHERE user_id = ? AND status = 'active'
                ORDER BY start_date DESC LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'subscription_tier': 'free', 'api_calls_used': 0, 'api_calls_limit': 5}

    
    def get_company_subscription(self, company_id: int) -> Dict:
        """Get company's subscription details"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT plan as subscription_tier, status, start_date, end_date,
                    analyses_limit as max_projects
                FROM subscriptions 
                WHERE company_id = ? AND status = 'active'
                ORDER BY start_date DESC LIMIT 1
            """, (company_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'subscription_tier': 'free', 'max_users': 5, 'max_projects': 5}

    
    def update_subscription(self, user_id: int = None, company_id: int = None,
                           tier: str = None, expiry_days: int = None) -> bool:
        """Update subscription for user or company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if user_id:
                updates = ["subscription_tier = ?"]
                values = [tier]
                
                if expiry_days:
                    updates.append("subscription_expiry = DATE('now', ?)")
                    values.append(f"+{expiry_days} days")
                
                values.append(user_id)
                cursor.execute(f"""
                    UPDATE users 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
                
            elif company_id:
                updates = ["subscription_tier = ?"]
                values = [tier]
                
                if expiry_days:
                    updates.append("subscription_expiry = DATE('now', ?)")
                    values.append(f"+{expiry_days} days")
                
                values.append(company_id)
                cursor.execute(f"""
                    UPDATE companies 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
            else:
                return False
            
            return cursor.rowcount > 0
    
    def increment_api_usage(self, user_id: int) -> bool:
        """Increment API call count for user"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                UPDATE users 
                SET api_calls_used = api_calls_used + 1
                WHERE id = ? AND api_calls_used < api_calls_limit
            """, (user_id,))
            
            return cursor.rowcount > 0
    
    # ==================== TENDER ANALYSIS METHODS ====================
    
    def save_analysis(self, user_id: int, tender_id: str, analysis_data: Dict,
                     confidence_score: float = None) -> int:
        """Save tender analysis results"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            cursor.execute("""
                INSERT INTO tender_analyses 
                (user_id, tender_id, analysis_data, confidence_score, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, tender_id, json.dumps(analysis_data), confidence_score))
            
            return cursor.lastrowid
    
    # database/crud_operations.py - Fixed get_user_analyses

    def get_user_analyses(self, user_id: int, company_id: int = None, role: str = 'user', limit: int = 50):
        """Get user's tender analyses with role-based filtering"""
        
        # Use the correct context manager pattern
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            print(f"🔍 get_user_analyses called with: user_id={user_id}, company_id={company_id}, role={role}")
            
            # System admin can see all analyses across all companies
            if role in ['admin', 'system_admin']:
                cursor.execute('''
                    SELECT * FROM tender_analyses 
                    ORDER BY analysis_date DESC LIMIT ?
                ''', (limit,))
            # Company admin and manager can see all analyses for their company
            elif role in ['company_admin', 'manager'] and company_id:
                cursor.execute('''
                    SELECT * FROM tender_analyses 
                    WHERE company_id = ? 
                    ORDER BY analysis_date DESC LIMIT ?
                ''', (company_id, limit))
            # Regular users can only see their own analyses
            else:
                cursor.execute('''
                    SELECT * FROM tender_analyses 
                    WHERE user_id = ? AND company_id = ?
                    ORDER BY analysis_date DESC LIMIT ?
                ''', (user_id, company_id, limit))
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            data = cursor.fetchall()
            
            print(f"🔍 Found {len(data)} analyses for role={role}, company_id={company_id}")
            
            if data:
                import pandas as pd
                df = pd.DataFrame(data, columns=columns)
                
                # Parse competitor_bids JSON if present
                if 'competitor_bids' in df.columns:
                    import json
                    def parse_competitor_bids(value):
                        if value is None:
                            return []
                        if isinstance(value, str):
                            try:
                                if value and value != 'null':
                                    return json.loads(value)
                            except:
                                pass
                        return []
                    df['competitor_bids'] = df['competitor_bids'].apply(parse_competitor_bids)
                
                return df
            return pd.DataFrame()
    
    def get_company_stats(self, company_id: int) -> Dict:
        """Get analysis statistics for a company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Get user IDs for this company
            cursor.execute("SELECT id FROM users WHERE company_id = ?", (company_id,))
            user_ids = [row['id'] for row in cursor.fetchall()]
            
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
            
            placeholders = ','.join('?' * len(user_ids))
            
            # Get analysis stats
            cursor.execute(f"""
                SELECT COUNT(*) as total, AVG(confidence_score) as avg_conf,
                    SUM(CASE WHEN bid_status = 'won' THEN 1 ELSE 0 END) as wins,
                    COUNT(CASE WHEN bid_status IS NOT NULL THEN 1 END) as total_bids
                FROM tender_analyses
                WHERE user_id IN ({placeholders})
            """, user_ids)
            
            row = cursor.fetchone()
            
            if row:
                stats['total_analyses'] = row['total'] or 0
                stats['avg_confidence'] = row['avg_conf'] or 0
                stats['total_bids'] = row['total_bids'] or 0
                stats['total_wins'] = row['wins'] or 0
                
                if stats['total_bids'] > 0:
                    stats['win_rate'] = (stats['total_wins'] / stats['total_bids']) * 100
            
            return stats

    
    def toggle_favorite_analysis(self, analysis_id: int, user_id: int) -> bool:
        """Toggle favorite status of an analysis"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                UPDATE tender_analyses
                SET is_favorite = NOT is_favorite
                WHERE id = ? AND user_id = ?
            """, (analysis_id, user_id))
            
            return cursor.rowcount > 0
    
    # ==================== HISTORICAL TENDER METHODS ====================
    
    def save_historical_tender(self, tender_data: Dict) -> int:
        """Save historical tender data"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            cursor.execute("""
                INSERT OR REPLACE INTO historical_tenders
                (tender_id, title, procuring_entity, estimated_amount, awarded_amount,
                 award_date, contractor, contract_period, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tender_data.get('tender_id'),
                tender_data.get('title'),
                tender_data.get('procuring_entity'),
                tender_data.get('estimated_amount'),
                tender_data.get('awarded_amount'),
                tender_data.get('award_date'),
                tender_data.get('contractor'),
                tender_data.get('contract_period'),
                tender_data.get('category')
            ))
            
            return cursor.lastrowid
    
    def get_historical_tenders(self, filters: Dict = None, limit: int = 100) -> List[Dict]:
        """Get historical tenders with optional filters"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = "SELECT * FROM historical_tenders WHERE 1=1"
            values = []
            
            if filters:
                if 'procuring_entity' in filters:
                    query += " AND procuring_entity LIKE ?"
                    values.append(f"%{filters['procuring_entity']}%")
                
                if 'category' in filters:
                    query += " AND category = ?"
                    values.append(filters['category'])
                
                if 'min_amount' in filters:
                    query += " AND awarded_amount >= ?"
                    values.append(filters['min_amount'])
                
                if 'max_amount' in filters:
                    query += " AND awarded_amount <= ?"
                    values.append(filters['max_amount'])
                
                if 'from_date' in filters:
                    query += " AND award_date >= ?"
                    values.append(filters['from_date'])
                
                if 'to_date' in filters:
                    query += " AND award_date <= ?"
                    values.append(filters['to_date'])
            
            query += " ORDER BY award_date DESC LIMIT ?"
            values.append(limit)
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_winning_statistics(self, contractor_name: str = None) -> Dict:
        """Get winning statistics for contractors"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if contractor_name:
                cursor.execute("""
                    SELECT contractor, COUNT(*) as wins, 
                           AVG(awarded_amount) as avg_amount,
                           SUM(awarded_amount) as total_amount,
                           MIN(award_date) as first_win,
                           MAX(award_date) as last_win
                    FROM historical_tenders
                    WHERE contractor = ?
                    GROUP BY contractor
                """, (contractor_name,))
            else:
                cursor.execute("""
                    SELECT contractor, COUNT(*) as wins, 
                           AVG(awarded_amount) as avg_amount,
                           SUM(awarded_amount) as total_amount,
                           MIN(award_date) as first_win,
                           MAX(award_date) as last_win
                    FROM historical_tenders
                    WHERE contractor IS NOT NULL
                    GROUP BY contractor
                    ORDER BY wins DESC
                    LIMIT 50
                """)
            
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    # ==================== COMPETITOR METHODS ====================
    
    def get_competitor_master_list(self, company_id: int) -> List[Dict]:
        """Get competitor master list for a company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT c.*, 
                       COUNT(DISTINCT ct.tender_id) as tracked_tenders,
                       MAX(ct.last_updated) as last_activity
                FROM competitors c
                LEFT JOIN competitor_tracking ct ON c.id = ct.competitor_id
                WHERE c.company_id = ?
                GROUP BY c.id
                ORDER BY c.name
            """, (company_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_competitor_to_master(self, company_id: int, name: str, 
                                 registration_no: str = None, 
                                 website: str = None) -> int:
        """Add competitor to master list"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO competitors (company_id, name, registration_no, website)
                VALUES (?, ?, ?, ?)
            """, (company_id, name, registration_no, website))
            
            return cursor.lastrowid
    
    def update_competitor_info(self, competitor_id: int, **kwargs) -> bool:
        """Update competitor information"""
        allowed_fields = ['name', 'registration_no', 'website', 'notes']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(competitor_id)
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                UPDATE competitors 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def track_competitor_tender(self, competitor_id: int, tender_id: str, 
                               amount: float = None, status: str = 'tracking') -> int:
        """Track a competitor's tender activity"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO competitor_tracking (competitor_id, tender_id, amount, status)
                VALUES (?, ?, ?, ?)
            """, (competitor_id, tender_id, amount, status))
            
            return cursor.lastrowid
    
    # ==================== KNOWLEDGE REPOSITORY METHODS ====================
    
    # Personnel Management
    def add_personnel(self, company_id: int, name: str, designation: str,
                     expertise_areas: str, years_experience: int,
                     certifications: str = None, cv_path: str = None) -> int:
        """Add personnel to knowledge repository"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO personnel (company_id, name, designation, expertise_areas,
                                     years_experience, certifications, cv_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, name, designation, expertise_areas,
                  years_experience, certifications, cv_path))
            
            return cursor.lastrowid
    
    def get_personnel(self, company_id: int, expertise: str = None) -> List[Dict]:
        """Get personnel list with optional expertise filter"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = "SELECT * FROM personnel WHERE company_id = ?"
            values = [company_id]
            
            if expertise:
                query += " AND expertise_areas LIKE ?"
                values.append(f"%{expertise}%")
            
            query += " ORDER BY years_experience DESC"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_personnel(self, personnel_id: int, **kwargs) -> bool:
        """Update personnel information"""
        allowed_fields = ['name', 'designation', 'expertise_areas', 
                         'years_experience', 'certifications', 'cv_path']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(personnel_id)
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                UPDATE personnel 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    # Equipment Management
    def add_equipment(self, company_id: int, name: str, type: str,
                     specifications: str, quantity: int, condition: str,
                     ownership: str, value: float = None) -> int:
        """Add equipment to knowledge repository"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO equipment (company_id, name, type, specifications,
                                     quantity, condition, ownership, value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, name, type, specifications,
                  quantity, condition, ownership, value))
            
            return cursor.lastrowid
    
    def get_equipment(self, company_id: int, equipment_type: str = None) -> List[Dict]:
        """Get equipment list with optional type filter"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = "SELECT * FROM equipment WHERE company_id = ?"
            values = [company_id]
            
            if equipment_type:
                query += " AND type = ?"
                values.append(equipment_type)
            
            query += " ORDER BY name"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    # Experience Management
    def add_experience(self, company_id: int, project_name: str,
                      client_name: str, contract_value: float,
                      completion_date: str, project_type: str,
                      description: str = None) -> int:
        """Add project experience to knowledge repository"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO experiences (company_id, project_name, client_name,
                                       contract_value, completion_date,
                                       project_type, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, project_name, client_name,
                  contract_value, completion_date, project_type, description))
            
            return cursor.lastrowid
    
    def get_experiences(self, company_id: int, project_type: str = None,
                       min_value: float = None) -> List[Dict]:
        """Get project experiences with filters"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = "SELECT * FROM experiences WHERE company_id = ?"
            values = [company_id]
            
            if project_type:
                query += " AND project_type = ?"
                values.append(project_type)
            
            if min_value:
                query += " AND contract_value >= ?"
                values.append(min_value)
            
            query += " ORDER BY completion_date DESC"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    # Financial Management
    def add_financial_capacity(self, company_id: int, fiscal_year: str,
                              annual_turnover: float, net_profit: float,
                              liquid_assets: float, credit_limit: float) -> int:
        """Add financial capacity record"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO financial_records (company_id, fiscal_year, annual_turnover,
                                             net_profit, liquid_assets, credit_limit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_id, fiscal_year, annual_turnover,
                  net_profit, liquid_assets, credit_limit))
            
            return cursor.lastrowid
    
    def get_financial_records(self, company_id: int, 
                             fiscal_year: str = None) -> List[Dict]:
        """Get financial records for a company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = "SELECT * FROM financial_records WHERE company_id = ?"
            values = [company_id]
            
            if fiscal_year:
                query += " AND fiscal_year = ?"
                values.append(fiscal_year)
            
            query += " ORDER BY fiscal_year DESC"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== DOCUMENT MANAGEMENT METHODS ====================
    
    def add_document(self, user_id: int, company_id: int, filename: str,
                    file_path: str, document_type: str, metadata: Dict = None) -> int:
        """Add document to repository"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO documents (user_id, company_id, filename, file_path,
                                     document_type, metadata, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, company_id, filename, file_path,
                  document_type, json.dumps(metadata) if metadata else None))
            
            return cursor.lastrowid
    
    def update_document(self, document_id: int, **kwargs) -> bool:
        """Update document metadata"""
        allowed_fields = ['filename', 'document_type', 'metadata']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == 'metadata' and value:
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(document_id)
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                UPDATE documents 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def get_documents(self, company_id: int, document_type: str = None,
                     limit: int = 100) -> List[Dict]:
        """Get documents for a company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = """
                SELECT d.*, u.username as uploaded_by
                FROM documents d
                LEFT JOIN users u ON d.user_id = u.id
                WHERE d.company_id = ?
            """
            values = [company_id]
            
            if document_type:
                query += " AND d.document_type = ?"
                values.append(document_type)
            
            query += " ORDER BY d.uploaded_at DESC LIMIT ?"
            values.append(limit)
            
            cursor.execute(query, values)
            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc.get('metadata'):
                    doc['metadata'] = json.loads(doc['metadata'])
                documents.append(doc)
            
            return documents
    
    def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a document"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                DELETE FROM documents 
                WHERE id = ? AND user_id = ?
            """, (document_id, user_id))
            
            return cursor.rowcount > 0
    
    # ==================== SEMANTIC SEARCH METHODS ====================
    
    def store_embedding(self, content_type: str, content_id: int,
                       content_text: str, embedding_blob: bytes) -> bool:
        """Store embedding vector for semantic search"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings
                (content_type, content_id, content_text, embedding, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (content_type, content_id, content_text, embedding_blob))
            
            return cursor.rowcount > 0
    
    def semantic_search(self, query_embedding: bytes, content_type: str = None,
                       limit: int = 10) -> List[Dict]:
        """
        Perform semantic search using cosine similarity
        Note: This is a simplified version. In production, use vector similarity
        """
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # For SQLite without vector extension, we'll retrieve candidates
            # and compute similarity in Python (not efficient for large datasets)
            query = "SELECT content_type, content_id, content_text FROM embeddings"
            values = []
            
            if content_type:
                query += " WHERE content_type = ?"
                values.append(content_type)
            
            cursor.execute(query, values)
            
            # Here you would implement cosine similarity calculation
            # This is a placeholder - implement actual similarity search
            results = []
            for row in cursor.fetchall():
                results.append({
                    'content_type': row['content_type'],
                    'content_id': row['content_id'],
                    'content_text': row['content_text'],
                    'similarity_score': 0.0  # Placeholder
                })
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:limit]
    
    def hybrid_search(self, query_text: str, query_embedding: bytes = None,
                     content_type: str = None, limit: int = 10) -> List[Dict]:
        """Combine keyword and semantic search"""
        # Keyword search results
        keyword_results = self.keyword_search(query_text, content_type, limit*2)
        
        # Semantic search results if embedding provided
        semantic_results = []
        if query_embedding:
            semantic_results = self.semantic_search(query_embedding, content_type, limit*2)
        
        # Merge and deduplicate results (simplified)
        all_results = keyword_results + semantic_results
        seen = set()
        unique_results = []
        
        for result in all_results:
            key = f"{result.get('content_type')}_{result.get('content_id')}"
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results[:limit]
    
    def keyword_search(self, query: str, content_type: str = None,
                      limit: int = 10) -> List[Dict]:
        """Perform keyword-based search across knowledge repository"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            results = []
            
            # Search in personnel
            if not content_type or content_type == 'personnel':
                cursor.execute("""
                    SELECT 'personnel' as content_type, id as content_id,
                           name as title, expertise_areas as content,
                           designation as extra_info
                    FROM personnel
                    WHERE name LIKE ? OR expertise_areas LIKE ? OR designation LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search in equipment
            if not content_type or content_type == 'equipment':
                cursor.execute("""
                    SELECT 'equipment' as content_type, id as content_id,
                           name as title, specifications as content,
                           type as extra_info
                    FROM equipment
                    WHERE name LIKE ? OR specifications LIKE ? OR type LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search in experiences
            if not content_type or content_type == 'experience':
                cursor.execute("""
                    SELECT 'experience' as content_type, id as content_id,
                           project_name as title, description as content,
                           client_name as extra_info
                    FROM experiences
                    WHERE project_name LIKE ? OR description LIKE ? OR client_name LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            return results[:limit]
    
    # ==================== AUTO-FILL METHODS ====================
    
    def get_auto_fill_data(self, company_id: int, field_type: str) -> List[Dict]:
        """Get auto-fill suggestions based on field type"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if field_type == 'personnel':
                cursor.execute("""
                    SELECT id, name, designation, expertise_areas
                    FROM personnel
                    WHERE company_id = ?
                    ORDER BY years_experience DESC
                """, (company_id,))
                
            elif field_type == 'equipment':
                cursor.execute("""
                    SELECT id, name, type, specifications
                    FROM equipment
                    WHERE company_id = ?
                    ORDER BY name
                """, (company_id,))
                
            elif field_type == 'experience':
                cursor.execute("""
                    SELECT id, project_name, client_name, contract_value, project_type
                    FROM experiences
                    WHERE company_id = ?
                    ORDER BY completion_date DESC
                    LIMIT 20
                """, (company_id,))
                
            elif field_type == 'financial':
                cursor.execute("""
                    SELECT fiscal_year, annual_turnover, net_profit, liquid_assets
                    FROM financial_records
                    WHERE company_id = ?
                    ORDER BY fiscal_year DESC
                    LIMIT 5
                """, (company_id,))
            else:
                return []
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_knowledge_base(self, company_id: int, search_term: str,
                             category: str = None) -> List[Dict]:
        """Search across knowledge repository for auto-fill"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            results = []
            
            if not category or category == 'personnel':
                cursor.execute("""
                    SELECT 'personnel' as source, id, name, designation as info
                    FROM personnel
                    WHERE company_id = ? AND (name LIKE ? OR expertise_areas LIKE ?)
                    LIMIT 10
                """, (company_id, f"%{search_term}%", f"%{search_term}%"))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            if not category or category == 'equipment':
                cursor.execute("""
                    SELECT 'equipment' as source, id, name, type as info
                    FROM equipment
                    WHERE company_id = ? AND (name LIKE ? OR type LIKE ?)
                    LIMIT 10
                """, (company_id, f"%{search_term}%", f"%{search_term}%"))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            if not category or category == 'experience':
                cursor.execute("""
                    SELECT 'experience' as source, id, project_name as name,
                           client_name as info
                    FROM experiences
                    WHERE company_id = ? AND (project_name LIKE ? OR client_name LIKE ?)
                    LIMIT 10
                """, (company_id, f"%{search_term}%", f"%{search_term}%"))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            return results
    
    # ==================== EXTENSION TRACKING METHODS ====================
    
    def get_extension_fill_usage(self, user_id: int, days: int = 30) -> Dict:
        """Get extension auto-fill usage statistics"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT field_type, COUNT(*) as usage_count,
                       MAX(used_at) as last_used
                FROM extension_fill_log
                WHERE user_id = ? AND used_at >= DATE('now', ?)
                GROUP BY field_type
            """, (user_id, f"-{days} days"))
            
            usage = {row['field_type']: row['usage_count'] for row in cursor.fetchall()}
            return usage
    
    def log_extension_fill(self, user_id: int, field_type: str,
                          source_type: str, source_id: int) -> bool:
        """Log extension auto-fill usage"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                INSERT INTO extension_fill_log (user_id, field_type, source_type, source_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, field_type, source_type, source_id))
            
            return cursor.rowcount > 0
    
    # ==================== SCENARIO METHODS ====================
    
    def save_scenario(self, user_id: int, name: str, scenario_data: Dict,
                     is_shared: bool = False) -> int:
        """Save a tender scenario for future use"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            share_token = secrets.token_urlsafe(16) if is_shared else None
            
            cursor.execute("""
                INSERT INTO scenarios (user_id, name, scenario_data, is_shared, share_token)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, name, json.dumps(scenario_data), is_shared, share_token))
            
            return cursor.lastrowid
    
    def get_user_scenarios(self, user_id: int, include_shared: bool = False) -> List[Dict]:
        """Get scenarios for a user"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if include_shared:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE user_id = ? OR is_shared = 1
                    ORDER BY is_favorite DESC, updated_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE user_id = ?
                    ORDER BY is_favorite DESC, updated_at DESC
                """, (user_id,))
            
            scenarios = []
            for row in cursor.fetchall():
                scenario = dict(row)
                scenario['scenario_data'] = json.loads(scenario['scenario_data'])
                scenarios.append(scenario)
            
            return scenarios
    
    def get_scenario_by_id(self, scenario_id: int, user_id: int = None) -> Optional[Dict]:
        """Get scenario by ID with optional user ownership check"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if user_id:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE id = ? AND (user_id = ? OR is_shared = 1)
                """, (scenario_id, user_id))
            else:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE id = ?
                """, (scenario_id,))
            
            row = cursor.fetchone()
            if row:
                scenario = dict(row)
                scenario['scenario_data'] = json.loads(scenario['scenario_data'])
                return scenario
            return None
    
    def delete_scenario(self, scenario_id: int, user_id: int) -> bool:
        """Delete a scenario"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                DELETE FROM scenarios
                WHERE id = ? AND user_id = ?
            """, (scenario_id, user_id))
            
            return cursor.rowcount > 0
    
    def toggle_favorite_scenario(self, scenario_id: int, user_id: int) -> bool:
        """Toggle favorite status of a scenario"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                UPDATE scenarios
                SET is_favorite = NOT is_favorite
                WHERE id = ? AND user_id = ?
            """, (scenario_id, user_id))
            
            return cursor.rowcount > 0
    
    def update_scenario_name(self, scenario_id: int, user_id: int, new_name: str) -> bool:
        """Update scenario name"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                UPDATE scenarios
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (new_name, scenario_id, user_id))
            
            return cursor.rowcount > 0
    
    def share_scenario(self, scenario_id: int, user_id: int) -> Optional[str]:
        """Share a scenario and return share token"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            share_token = secrets.token_urlsafe(16)
            
            cursor.execute("""
                UPDATE scenarios
                SET is_shared = 1, share_token = ?
                WHERE id = ? AND user_id = ?
            """, (share_token, scenario_id, user_id))
            
            if cursor.rowcount > 0:
                return share_token
            return None
    
    def get_shared_scenario_by_token(self, share_token: str) -> Optional[Dict]:
        """Get shared scenario by token"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, user_id, name, scenario_data, created_at
                FROM scenarios
                WHERE share_token = ? AND is_shared = 1
            """, (share_token,))
            
            row = cursor.fetchone()
            if row:
                scenario = dict(row)
                scenario['scenario_data'] = json.loads(scenario['scenario_data'])
                return scenario
            return None
    
    # ==================== COMPANY MANAGEMENT METHODS ====================
    def validate_mobile_number(self, mobile: str) -> bool:
        """Validate Bangladeshi mobile number"""
        # Bangladesh mobile: 01XXXXXXXXX (11 digits)
        pattern = r'^01[3-9]\d{8}$'
        return bool(re.match(pattern, mobile))
    
    def get_all_companies_filtered(self, filters: Dict = None) -> List[Dict]:
        """Get all companies with optional filtering"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = "SELECT * FROM companies WHERE 1=1"
            values = []
            
            if filters:
                if 'subscription_tier' in filters:
                    query += " AND subscription_tier = ?"
                    values.append(filters['subscription_tier'])
                
                if 'is_active' in filters:
                    query += " AND is_active = ?"
                    values.append(filters['is_active'])
                
                if 'name' in filters:
                    query += " AND name LIKE ?"
                    values.append(f"%{filters['name']}%")
            
            query += " ORDER BY name"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    def create_company(self, company_name: str, mobile_number: str = None,
                       email: str = None, address: str = None,
                       registration_no: str = None) -> Optional[int]:
        """Create a new company with unique mobile number"""
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Validate mobile if provided
            if mobile_number:
                mobile_number = self.normalize_mobile(mobile_number)
                if not self.validate_bangladesh_mobile(mobile_number):
                    raise ValueError(f"Invalid mobile number: {mobile_number}")
                
                # Check if mobile already exists
                cursor.execute("SELECT id FROM companies WHERE mobile_number = ?", (mobile_number,))
                if cursor.fetchone():
                    raise ValueError(f"Mobile number {mobile_number} is already registered")
            
            # Check if company name with same mobile exists
            if company_name and mobile_number:
                cursor.execute(
                    "SELECT id FROM companies WHERE company_name = ? AND mobile_number = ?",
                    (company_name, mobile_number)
                )
                if cursor.fetchone():
                    raise ValueError(f"Company {company_name} with mobile {mobile_number} already exists")
            
            # Create company
            cursor.execute("""
                INSERT INTO companies (company_name, mobile_number, email, address, registration_no, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (company_name, mobile_number, email, address, registration_no))
            
            return cursor.lastrowid
    
    def get_company_by_id(self, company_id: int) -> Optional[Dict]:
        """Get company by ID"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, company_name, mobile_number, email, address, 
                    registration_number, phone, division, district, 
                    is_active, created_at
                FROM companies 
                WHERE id = ?
            """, (company_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None

    
    def get_company_by_mobile(self, mobile_number: str) -> Optional[Dict]:
        """Get company by mobile number"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, company_name, mobile_number, email, address, 
                    registration_number, phone, division, district, 
                    is_active, created_at
                FROM companies 
                WHERE mobile_number = ?
            """, (mobile_number,))
            
            row = cursor.fetchone()
            return dict(row) if row else None


    
    
    def update_company(self, company_id: int, **kwargs) -> bool:
        """Update company information"""
        allowed_fields = ['name', 'registration_no', 'address', 'phone', 'email',
                         'subscription_tier', 'is_active', 'max_users', 'max_projects']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(company_id)
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                UPDATE companies 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def delete_company(self, company_id: int, hard_delete: bool = False) -> bool:
        """Delete or deactivate company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            if hard_delete:
                cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            else:
                cursor.execute("UPDATE companies SET is_active = 0 WHERE id = ?", (company_id,))
            
            return cursor.rowcount > 0
    
    # ==================== ROLE/PERMISSION METHODS ====================
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT permission
                FROM role_permissions
                WHERE role = ?
            """, (role,))
            
            return [row['permission'] for row in cursor.fetchall()]
    
    def get_all_roles(self) -> List[Dict]:
        """Get all roles with their permissions"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT role, GROUP_CONCAT(permission) as permissions
                FROM role_permissions
                GROUP BY role
                ORDER BY role
            """)
            
            roles = []
            for row in cursor.fetchall():
                roles.append({
                    'role': row['role'],
                    'permissions': row['permissions'].split(',') if row['permissions'] else []
                })
            
            return roles
    
    def update_role_permissions(self, role: str, permissions: List[str]) -> bool:
        """Update permissions for a role"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            # Delete existing permissions
            cursor.execute("DELETE FROM role_permissions WHERE role = ?", (role,))
            
            # Insert new permissions
            for permission in permissions:
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission)
                    VALUES (?, ?)
                """, (role, permission))
            
            return True
    
    # ==================== PWD/LGED RATE METHODS ====================
    
    def get_pwd_chapters(self) -> List[Dict]:
        """Get all PWD schedule chapters"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT chapter_code, chapter_name, version, effective_date
                FROM pwd_schedule
                WHERE parent_code IS NULL
                ORDER BY chapter_code
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_lged_chapters(self) -> List[Dict]:
        """Get all LGED schedule chapters"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT chapter_code, chapter_name, version, effective_date
                FROM lged_schedule
                WHERE parent_code IS NULL
                ORDER BY chapter_code
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pwd_children(self, parent_code: str) -> List[Dict]:
        """Get child items for a PWD schedule parent"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT item_code, description, unit, rate_bdt, parent_code
                FROM pwd_schedule
                WHERE parent_code = ?
                ORDER BY item_code
            """, (parent_code,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pwd_stats(self, chapter_code: str = None) -> Dict:
        """Get statistics for PWD schedule"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            query = """
                SELECT COUNT(*) as total_items,
                       AVG(rate_bdt) as avg_rate,
                       MIN(rate_bdt) as min_rate,
                       MAX(rate_bdt) as max_rate
                FROM pwd_schedule
                WHERE rate_bdt IS NOT NULL
            """
            values = []
            
            if chapter_code:
                query += " AND chapter_code = ?"
                values.append(chapter_code)
            
            cursor.execute(query, values)
            row = cursor.fetchone()
            
            return dict(row) if row else {}
    
    def search_pwd_schedule(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search PWD schedule items"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM pwd_schedule
                WHERE description LIKE ? OR item_code LIKE ?
                ORDER BY item_code
                LIMIT ?
            """, (f"%{search_term}%", f"%{search_term}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_lged_schedule(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search LGED schedule items"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM lged_schedule
                WHERE description LIKE ? OR item_code LIKE ?
                ORDER BY item_code
                LIMIT ?
            """, (f"%{search_term}%", f"%{search_term}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_rate_by_item_code(self, schedule_type: str, item_code: str) -> Optional[Dict]:
        """Get rate by item code from specified schedule"""
        table = 'pwd_schedule' if schedule_type == 'pwd' else 'lged_schedule'
        
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM {table}
                WHERE item_code = ?
            """, (item_code,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def calculate_win_probability(tender_id, user_total_cost):
        """
        Evaluates historical competitor price ranges for the same tender 
        to calculate a statistical win probability percentage.
        """
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT total_bid_amount FROM competitor_bids WHERE tender_id = ?"
        df_comp = pd.read_sql_query(query, conn, params=(tender_id,))
        conn.close()
        
        if df_comp.empty:
            return None, "No data available"
            
        all_bids = df_comp['total_bid_amount'].tolist()
        all_bids.append(user_total_cost)
        all_bids.sort()
        
        # Find rank index positioning (Lower price is preferred in e-GP L1 procurement formats)
        rank = all_bids.index(user_total_cost) + 1
        total_bidders = len(all_bids)
        
        # Calculate probability: higher ranking position results in a stronger win margin
        probability = ((total_bidders - rank) / total_bidders) * 100
        return round(probability, 1), f"Rank {rank} of {total_bidders}"

    
    @st.cache_data(ttl=300)
    def get_company_tenders_cached(company_id: int) -> pd.DataFrame:
        """Cached helper to fetch company tenders as DataFrame"""
        try:
            conn = db.get_connection()
            cursor = self.db_conn.get_cursor(conn)
            
            cursor.execute('''
            SELECT 
                t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
                t.division, t.district, t.thana, t.country, t.procurement_type,
                t.official_estimate, t.submission_deadline, t.tender_security,
                t.document_fee, t.evaluation_type,
                t.is_locked, t.is_copy, t.original_tender_id, t.is_active,
                t.created_at, t.updated_at
            FROM company_tenders t
            WHERE t.company_id = ? 
            ORDER BY t.created_at DESC
            ''', (company_id,))
            
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            conn.close()
            
            return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
            
        except Exception as e:
            print(f"Failed to fetch cached tenders: {e}")
            return pd.DataFrame()
                