# database/crud_user.py - Fixed version with proper placeholder handling

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import logging
import secrets
import string
import bcrypt
import re

logger = logging.getLogger(__name__)


class UserCRUD:
    """User-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get the database manager - works both as standalone and when bound"""
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        elif self._db_manager:
            return self._db_manager
        else:
            from database.unified_db_manager import get_db_manager
            return get_db_manager()
    
    # =========================================================================
    # USER OPERATIONS
    # =========================================================================
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        db = self._get_db()
        
        return db.query_one("""
            SELECT 
                id, username, email, full_name, phone, mobile_number,
                role, is_active, created_at, last_login, company_id,
                mobile_verified, email_verified, avatar_url, bio,
                location, website, specialization, years_experience,
                auth_provider, auth_provider_user_id, google_id,
                google_email, google_picture, created_by, is_approved,
                registration_complete
            FROM users 
            WHERE id = ?
        """, (user_id,))
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        db = self._get_db()
        
        return db.query_one("""
            SELECT 
                id, username, email, full_name, phone, mobile_number,
                role, is_active, created_at, last_login, company_id,
                mobile_verified, email_verified, avatar_url, bio,
                location, website, specialization, years_experience,
                auth_provider, auth_provider_user_id, google_id,
                google_email, google_picture, created_by, is_approved,
                registration_complete
            FROM users 
            WHERE email = ?
        """, (email,))
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        db = self._get_db()
        
        return db.query_one("""
            SELECT id, username, email FROM users WHERE username = ?
        """, (username,))
    
    def get_all_users(self, company_id: Optional[int] = None, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users with optional filters - works with both SQLite and Supabase"""
        db = self._get_db()
        
        # ✅ If using Supabase, use direct client
        if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
            try:
                # Build query
                query = db.supabase.table('users').select('*, companies!left(company_name)')
                
                # Apply filters
                if company_id:
                    query = query.eq('company_id', company_id)
                
                if role:
                    query = query.eq('role', role)
                
                # Order by created_at descending
                query = query.order('created_at', desc=True)
                
                response = query.execute()
                users = response.data if response.data else []
                
                # Format results
                formatted_users = []
                for row in users:
                    # Get company_name from nested object
                    company_data = row.get('companies')
                    company_name = company_data.get('company_name') if company_data else None
                    
                    formatted_users.append({
                        'id': row.get('id'),
                        'username': row.get('username'),
                        'email': row.get('email'),
                        'full_name': row.get('full_name'),
                        'phone': row.get('phone', ''),
                        'mobile_number': row.get('mobile_number', ''),
                        'mobile_verified': bool(row.get('mobile_verified', False)),
                        'email_verified': bool(row.get('email_verified', False)),
                        'role': row.get('role', 'viewer'),
                        'is_active': bool(row.get('is_active', True)),
                        'created_at': row.get('created_at'),
                        'last_login': row.get('last_login'),
                        'company_id': row.get('company_id'),
                        'company_name': company_name,
                        'avatar_url': row.get('avatar_url'),
                        'bio': row.get('bio'),
                        'location': row.get('location'),
                        'website': row.get('website'),
                        'specialization': row.get('specialization'),
                        'years_experience': row.get('years_experience'),
                        'is_approved': bool(row.get('is_approved', True)),
                        'registration_complete': bool(row.get('registration_complete', False))
                    })
                
                return formatted_users
                
            except Exception as e:
                print(f"⚠️ Supabase users query error: {e}")
                # Fall through to SQLite fallback
        
        # ============================================================
        # SQLite / Generic Fallback
        # ============================================================
        
        query = """
            SELECT 
                u.id, u.username, u.email, u.full_name, u.phone,
                u.mobile_number, u.mobile_verified, u.role,
                u.is_active, u.created_at, u.last_login, u.company_id,
                u.avatar_url, u.bio, u.location, u.website,
                u.specialization, u.years_experience,
                u.is_approved, u.registration_complete,
                c.company_name
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE 1=1
        """
        params = []
        
        if company_id:
            query += " AND u.company_id = ?"
            params.append(company_id)
        
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        query += " ORDER BY u.created_at DESC"
        
        try:
            results = db.query(query, tuple(params) if params else None)
        except Exception as e:
            print(f"⚠️ Users query error: {e}")
            results = []
        
        # Normalize boolean values
        for row in results:
            row['is_active'] = bool(row.get('is_active', False))
            row['mobile_verified'] = bool(row.get('mobile_verified', False))
            row['email_verified'] = bool(row.get('email_verified', False))
            row['is_approved'] = bool(row.get('is_approved', False))
            row['registration_complete'] = bool(row.get('registration_complete', False))
        
        return results
    
    def get_all_users_filtered(self, company_id=None, search="", role="", status=None, limit=20, offset=0):
        """
        Get users filtered by company, search, role, status
        Works with both SQLite and Supabase
        """
        db = self._get_db()
        
        # ✅ If using Supabase, use direct client
        if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
            try:
                # Build query with count
                query = db.supabase.table('users').select('*, companies!left(company_name)', count='exact')
                
                # Apply filters
                if company_id == -1:
                    query = query.is_('company_id', None)
                elif company_id and company_id > 0:
                    query = query.eq('company_id', company_id)
                
                if search:
                    query = query.or_(f"username.ilike.*{search}*,email.ilike.*{search}*,full_name.ilike.*{search}*")
                
                if role:
                    query = query.eq('role', role)
                
                if status is not None:
                    query = query.eq('is_active', 1 if status else 0)
                
                # Get total count first
                count_response = query.execute()
                total = count_response.count if hasattr(count_response, 'count') else 0
                
                # Apply pagination
                query = query.range(offset, offset + limit - 1)
                query = query.order('created_at', desc=True)
                
                response = query.execute()
                users = response.data if response.data else []
                
                # Format results
                formatted_users = []
                for row in users:
                    # Get company_name from nested object
                    company_data = row.get('companies')
                    company_name = company_data.get('company_name') if company_data else None
                    
                    formatted_users.append({
                        'id': row.get('id'),
                        'username': row.get('username'),
                        'email': row.get('email'),
                        'full_name': row.get('full_name'),
                        'phone': row.get('phone', ''),
                        'mobile_number': row.get('mobile_number', ''),
                        'mobile_verified': row.get('mobile_verified', 0),
                        'role': row.get('role', 'viewer'),
                        'is_active': row.get('is_active', 1),
                        'created_at': row.get('created_at'),
                        'last_login': row.get('last_login'),
                        'company_name': company_name,
                        'is_approved': row.get('is_approved', 1)
                    })
                
                return formatted_users, total
                
            except Exception as e:
                print(f"⚠️ Supabase users query error: {e}")
                # Fall through to SQLite fallback
        
        # ============================================================
        # SQLite / Generic Fallback
        # ============================================================
        
        query = """
            SELECT u.id, u.username, u.email, u.full_name, u.phone,
                u.mobile_number, u.mobile_verified,
                u.role, u.is_active, u.created_at, u.last_login, 
                c.company_name, u.is_approved
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE 1=1
        """
        params = []
        
        if company_id == -1:
            query += " AND u.company_id IS NULL"
        elif company_id and company_id > 0:
            query += " AND u.company_id = ?"
            params.append(company_id)
        
        if search:
            query += " AND (u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        if status is not None:
            query += " AND u.is_active = ?"
            params.append(1 if status else 0)
        
        # Get total count
        count_query = query.replace(
            "SELECT u.id, u.username, u.email, u.full_name, u.phone, u.mobile_number, u.mobile_verified, u.role, u.is_active, u.created_at, u.last_login, c.company_name, u.is_approved",
            "SELECT COUNT(*)"
        )
        
        try:
            count_result = self.query_one(count_query, tuple(params) if params else None)
            total = list(count_result.values())[0] if count_result else 0
        except Exception as e:
            print(f"⚠️ Count query error: {e}")
            total = 0
        
        # Add pagination
        query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            results = self.query(query, tuple(params) if params else None)
        except Exception as e:
            print(f"⚠️ Main query error: {e}")
            results = []
        
        # Format results
        users = []
        for row in results:
            users.append({
                'id': row.get('id'),
                'username': row.get('username'),
                'email': row.get('email'),
                'full_name': row.get('full_name'),
                'phone': row.get('phone', ''),
                'mobile_number': row.get('mobile_number', ''),
                'mobile_verified': row.get('mobile_verified', 0),
                'role': row.get('role', 'viewer'),
                'is_active': row.get('is_active', 1),
                'created_at': row.get('created_at'),
                'last_login': row.get('last_login'),
                'company_name': row.get('company_name'),
                'is_approved': row.get('is_approved', 1)
            })
        
        return users, total

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get complete user profile with social links"""
        db = self._get_db()
        
        # Get user data
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Get social links
        social_links = self.get_user_social_links(user_id)
        user['social_links'] = social_links
        
        return user
    
    def update_user_profile(self, user_id: int, **kwargs) -> bool:
        """Update user profile fields"""
        allowed_fields = [
            'full_name', 'phone', 'email', 'bio', 'location', 
            'website', 'avatar_url', 'specialization', 'years_experience'
        ]
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates[key] = value
        
        if not updates:
            return False
        
        return self.update_user(user_id, updates)
    
    def update_user_avatar(self, user_id: int, avatar_url: str) -> bool:
        """Update user avatar URL"""
        return self.update_user(user_id, {'avatar_url': avatar_url})
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user information"""
        db = self._get_db()
        
        try:
            allowed_fields = [
                'username', 'email', 'full_name', 'phone', 'mobile_number',
                'role', 'is_active', 'avatar_url', 'bio', 'location',
                'website', 'specialization', 'years_experience',
                'mobile_verified', 'email_verified', 'is_approved',
                'registration_complete', 'company_id'
            ]
            
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(user_id)
            
            db.execute(f"""
                UPDATE users 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, tuple(params))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Hard delete user (only allowed for non-admin users)"""
        db = self._get_db()
        try:
            # Check if user is admin
            row = db.query_one("SELECT role FROM users WHERE id = ?", (user_id,))
            if row and row.get('role') == 'admin':
                return False
            
            # Delete user and subscriptions
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            return True
        except Exception as e:
            logger.error(f"Delete user failed: {e}")
            return False
    
    def soft_delete_user(self, user_id: int) -> bool:
        """Soft delete a user (set is_active = 0)"""
        db = self._get_db()
        try:
            db.execute("""
                UPDATE users 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), user_id))
            return True
        except Exception as e:
            logger.error(f"Error soft deleting user: {e}")
            return False
    
    # =========================================================================
    # PASSWORD MANAGEMENT METHODS
    # =========================================================================
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its bcrypt hash"""
        print(f"🔍 _verify_password called for user {user_id}")
        # print(f"🔍 Using self._verify_password: {hasattr(self, '_verify_password')}")

        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except (bcrypt.InvalidHashError, ValueError, TypeError):
            return False

    def user_has_password(self, user_id: int) -> bool:
        """Check if user has a password set"""
        db = self._get_db()
        try:
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            query = "SELECT password FROM users WHERE id = ?"
            result = db.query_one(query, (user_id,))
            if result:
                password = result.get('password')
                return password is not None and password != ''
            return False
        except Exception as e:
            logger.error(f"Error checking if user has password: {e}")
            return False

    def change_user_password(self, user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password with verification of current password"""
        db = self._get_db()
        try:
            print(f"🔍 change_user_password called for user {user_id}")
            print(f"🔍 Using self._verify_password: {hasattr(self, '_verify_password')}")

            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            query = "SELECT password FROM users WHERE id = ?"
            result = db.query_one(query, (user_id,))
            
            if not result:
                return False, "User not found"
            
            stored_hash = result.get('password')
            
            if not stored_hash:
                return False, "No password set for this account. Please set a password first."
            
            # Verify current password
            if not self._verify_password(current_password, stored_hash):
                return False, "Current password is incorrect"
            
            # Hash new password
            hashed = self._hash_password(new_password)
            
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            update_query = """
                UPDATE users 
                SET password = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            db.execute(update_query, (hashed, user_id))
            
            # Log the activity
            self.log_user_activity(user_id, 'password_change', 'Password changed successfully')
            
            return True, "Password changed successfully"
            
        except Exception as e:
            logger.error(f"Password change failed for user {user_id}: {e}")
            return False, f"Failed to change password: {str(e)}"

    def set_user_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """Set password for OAuth user (no current password verification)"""
        db = self._get_db()
        try:
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            query = "SELECT id FROM users WHERE id = ?"
            result = db.query_one(query, (user_id,))
            
            if not result:
                return False, "User not found"
            
            # Hash new password
            hashed = self._hash_password(new_password)
            
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            update_query = """
                UPDATE users 
                SET password = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            db.execute(update_query, (hashed, user_id))
            
            # Log the activity
            self.log_user_activity(user_id, 'password_set', 'Password set for OAuth user')
            
            return True, "Password set successfully"
            
        except Exception as e:
            logger.error(f"Failed to set password for user {user_id}: {e}")
            return False, f"Failed to set password: {str(e)}"

    def reset_user_password(self, user_id: int, new_password: str = None) -> Tuple[bool, str]:
        """Reset user password. If new_password not provided, generate random."""
        db = self._get_db()
        try:
            # Generate password if not provided
            if not new_password:
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            # Hash the password
            hashed = self._hash_password(new_password)
            
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            update_query = """
                UPDATE users 
                SET password = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            db.execute(update_query, (hashed, user_id))
            
            # Check if any rows were affected
            check = db.query_one("SELECT id FROM users WHERE id = ?", (user_id,))
            if not check:
                return False, "User not found"
            
            # Log the activity
            self.log_user_activity(user_id, 'password_reset', 'Password was reset by admin')
            
            return True, new_password
            
        except Exception as e:
            logger.error(f"Password reset failed for user {user_id}: {e}")
            return False, f"Failed to reset password: {str(e)}"

    def generate_random_password(self) -> str:
        """Generate a random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(12))

    # =========================================================================
    # PASSWORD RESET TOKEN METHODS
    # =========================================================================
    
    def store_password_reset_token(self, email: str, token: str, expires_in_minutes: int = 60) -> bool:
        """Store password reset token"""
        db = self._get_db()
        try:
            expires_at = (datetime.now() + timedelta(minutes=expires_in_minutes)).isoformat()
            
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            db.execute("DELETE FROM password_reset_tokens WHERE email = ?", (email,))
            
            # Insert new token
            insert_query = """
                INSERT INTO password_reset_tokens (email, token, expires_at, created_at) 
                VALUES (?, ?, ?, ?)
            """
            db.execute(insert_query, (email, token, expires_at, datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Failed to store reset token: {e}")
            return False

    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify reset token and return email if valid"""
        db = self._get_db()
        try:
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            query = """
                SELECT email, expires_at 
                FROM password_reset_tokens 
                WHERE token = ? AND expires_at > ? AND used = FALSE
            """
            result = db.query_one(query, (token, datetime.now()))
            return result.get('email') if result else None
        except Exception as e:
            logger.error(f"Failed to verify reset token: {e}")
            return None

    def mark_token_as_used(self, token: str) -> bool:
        """Mark reset token as used"""
        db = self._get_db()
        try:
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            query = "UPDATE password_reset_tokens SET used = TRUE WHERE token = ?"
            db.execute(query, (token,))
            return True
        except Exception as e:
            logger.error(f"Failed to mark token as used: {e}")
            return False


    def update_password(self, email: str, new_password: str) -> bool:
        """Update user password with bcrypt"""
        db = self._get_db()
        try:
            hashed = self._hash_password(new_password)
            # ✅ FIXED: Use ? placeholder for both SQLite and Supabase
            query = "UPDATE users SET password = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?"
            db.execute(query, (hashed, email))
            return True
        except Exception as e:
            logger.error(f"Failed to update password: {e}")
            return False
    

    
    # =========================================================================
    # USER APPROVAL METHODS
    # =========================================================================
    
    def get_pending_users(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all pending approval users for a company"""
        db = self._get_db()
        return db.query("""
            SELECT id, username, email, full_name, phone, role, created_at, created_by
            FROM users 
            WHERE company_id = ? AND is_approved = 0 
            AND (registration_complete = 0 OR registration_complete IS NULL) 
            AND is_active = 1
            ORDER BY created_at ASC
        """, (company_id,))
    
    def get_all_pending_users(self) -> List[Dict[str, Any]]:
        """Get all pending user registrations across all companies (for system admin)"""
        db = self._get_db()
        return db.query("""
            SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, 
                u.created_at, u.created_by, c.company_name, u.is_approved, u.is_active
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE u.is_approved = 0
            ORDER BY u.created_at ASC
        """)
    
    def approve_user(self, user_id: int, approved_by: int) -> bool:
        """Approve a pending user registration"""
        db = self._get_db()
        try:
            db.execute("""
                UPDATE users 
                SET is_approved = 1, approved_by = ?, approved_at = ?
                WHERE id = ?
            """, (approved_by, datetime.now().isoformat(), user_id))
            
            db.execute("""
                UPDATE subscriptions 
                SET status = 'active', analyses_limit = 5
                WHERE user_id = ?
            """, (user_id,))
            return True
        except Exception as e:
            logger.error(f"Error approving user: {e}")
            return False
    
    def reject_user(self, user_id: int, rejected_by: int) -> bool:
        """Reject a pending user registration"""
        db = self._get_db()
        try:
            db.execute("""
                UPDATE users 
                SET is_active = 0, registration_complete = 0
                WHERE id = ?
            """, (user_id,))
            return True
        except Exception as e:
            logger.error(f"Error rejecting user: {e}")
            return False
    
    def is_user_approved(self, user_id: int) -> bool:
        """Check if user is approved"""
        db = self._get_db()
        result = db.query_one("SELECT is_approved, is_active FROM users WHERE id = ?", (user_id,))
        if result:
            return result.get('is_approved', 0) == 1 and result.get('is_active', 0) == 1
        return False
    
    # =========================================================================
    # USER ROLE & STATUS METHODS
    # =========================================================================
    
    def update_user_role(self, user_id: int, new_role: str, updated_by: int) -> bool:
        """Update user role"""
        db = self._get_db()
        try:
            db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            self.log_user_activity(user_id, 'role_change', f"Role changed to {new_role} by {updated_by}")
            return True
        except Exception as e:
            logger.error(f"Failed to update user role: {e}")
            return False
    
    def update_user_status(self, user_id: int, is_active: bool) -> bool:
        """Activate/deactivate user"""
        db = self._get_db()
        try:
            db.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
            return True
        except Exception as e:
            logger.error(f"Failed to update user status: {e}")
            return False
    
    def get_system_users(self) -> List[Dict[str, Any]]:
        """Get all system-level users (company_id IS NULL)"""
        db = self._get_db()
        results = db.query("""
            SELECT id, username, email, full_name, phone, 
                mobile_number, mobile_verified,
                role, is_active, created_at, last_login
            FROM users
            WHERE company_id IS NULL
            ORDER BY created_at DESC
        """)
        
        # Normalize boolean values
        for row in results:
            row['is_active'] = bool(row.get('is_active', False))
            row['mobile_verified'] = bool(row.get('mobile_verified', False))
        
        return results
    
    def get_company_users(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all users belonging to a specific company"""
        db = self._get_db()
        results = db.query("""
            SELECT id, username, email, full_name, phone, role, is_active, 
                created_at, last_login
            FROM users
            WHERE company_id = ?
            ORDER BY created_at DESC
        """, (company_id,))
        
        # Normalize boolean values
        for row in results:
            row['is_active'] = bool(row.get('is_active', False))
        
        return results
    
    # =========================================================================
    # USER CREATE METHODS
    # =========================================================================
    
    def create_system_user(self, user_data: Dict, created_by: int) -> Tuple[bool, any]:
        """Create a system-level user (no company)"""
        db = self._get_db()
        
        try:
            # Validate mobile number
            mobile = user_data.get('mobile_number', '')
            if not mobile:
                return False, "Mobile number is required"
            
            mobile = self._normalize_mobile(mobile)
            
            # Check if mobile already exists
            existing = db.query_one("SELECT id FROM users WHERE mobile_number = ?", (mobile,))
            if existing:
                return False, f"Mobile number {mobile} is already registered"
            
            # Check if email already exists
            existing = db.query_one("SELECT id FROM users WHERE email = ?", (user_data['email'],))
            if existing:
                return False, f"Email {user_data['email']} is already registered"
            
            # Check if username already exists
            existing = db.query_one("SELECT id FROM users WHERE username = ?", (user_data['username'],))
            if existing:
                return False, f"Username {user_data['username']} is already taken"
            
            # Hash password
            hashed = self._hash_password(user_data['password'])
            
            # Insert user
            db.execute("""
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, mobile_number, role,
                    is_active, created_by, is_approved, account_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                None,
                user_data['username'],
                hashed,
                user_data['email'],
                user_data['full_name'],
                user_data.get('phone', ''),
                mobile,
                user_data.get('role', 'viewer'),
                1,
                created_by,
                1,
                'system'
            ))
            
            # Get user ID
            result = db.query_one("SELECT id FROM users WHERE email = ?", (user_data['email'],))
            if result:
                user_id = result['id']
                # Create subscription
                db.execute("""
                    INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
                    VALUES (?, ?, ?, ?)
                """, (user_id, 'professional', 'active', -1))
                return True, user_id
            
            return False, "Failed to create user"
            
        except Exception as e:
            logger.error(f"Error creating system user: {e}")
            return False, str(e)
    
    def create_company_user(self, company_id: int, user_data: Dict, created_by: int) -> Tuple[bool, any]:
        """Create a user under a specific company"""
        db = self._get_db()
        
        try:
            # Validate mobile number
            mobile = user_data.get('mobile_number', '')
            if not mobile:
                return False, "Mobile number is required"
            
            mobile = self._normalize_mobile(mobile)
            
            # Check if mobile already exists
            existing = db.query_one("SELECT id FROM users WHERE mobile_number = ?", (mobile,))
            if existing:
                return False, f"Mobile number {mobile} is already registered"
            
            # Check if email already exists
            existing = db.query_one("SELECT id FROM users WHERE email = ?", (user_data['email'],))
            if existing:
                return False, f"Email {user_data['email']} is already registered"
            
            # Check if username already exists
            existing = db.query_one("SELECT id FROM users WHERE username = ?", (user_data['username'],))
            if existing:
                return False, f"Username {user_data['username']} is already taken"
            
            # Hash password
            hashed = self._hash_password(user_data['password'])
            
            # Insert user
            db.execute("""
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, mobile_number, role,
                    is_active, created_by, is_approved, account_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                user_data['username'],
                hashed,
                user_data['email'],
                user_data['full_name'],
                user_data.get('phone', ''),
                mobile,
                user_data.get('role', 'viewer'),
                1,
                created_by,
                1,
                'company'
            ))
            
            # Get user ID
            result = db.query_one("SELECT id FROM users WHERE email = ?", (user_data['email'],))
            if result:
                user_id = result['id']
                # Create subscription
                db.execute("""
                    INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
                    VALUES (?, ?, ?, ?)
                """, (user_id, 'free', 'active', 5))
                return True, user_id
            
            return False, "Failed to create user"
            
        except Exception as e:
            logger.error(f"Error creating company user: {e}")
            return False, str(e)
    
    # =========================================================================
    # SOCIAL LINKS OPERATIONS
    # =========================================================================
    
    def get_user_social_links(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all social links for a user"""
        db = self._get_db()
        
        return db.query("""
            SELECT id, user_id, platform, url, is_public, created_at,
                   is_active, icon, display_order
            FROM social_links
            WHERE user_id = ?
            ORDER BY display_order ASC, platform ASC
        """, (user_id,))
    
    def add_social_link(self, user_id: int, platform: str, url: str, 
                        is_public: bool = True, icon: str = None) -> bool:
        """Add a new social link"""
        db = self._get_db()
        
        try:
            # Validate platform
            valid_platforms = [
                'facebook', 'twitter', 'instagram', 'linkedin', 'github',
                'youtube', 'tiktok', 'pinterest', 'reddit', 'whatsapp',
                'telegram', 'discord', 'slack', 'medium', 'dev.to'
            ]
            
            if platform.lower() not in valid_platforms:
                return False
            
            # Check if platform already exists
            existing = db.query_one("""
                SELECT id FROM social_links 
                WHERE user_id = ? AND platform = ?
            """, (user_id, platform.lower()))
            
            if existing:
                return False
            
            # Get max display order
            max_order = db.query_one("""
                SELECT MAX(display_order) as max_order 
                FROM social_links 
                WHERE user_id = ?
            """, (user_id,))
            
            display_order = (max_order.get('max_order') or -1) + 1 if max_order else 0
            
            db.execute("""
                INSERT INTO social_links 
                (user_id, platform, url, is_public, icon, display_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, platform.lower(), url, is_public, icon, display_order, datetime.now().isoformat()))
            
            return True
        except Exception as e:
            logger.error(f"Error adding social link: {e}")
            return False
    
    def update_social_link(self, link_id: int, updates: Dict[str, Any]) -> bool:
        """Update a social link"""
        db = self._get_db()
        
        try:
            allowed_fields = ['platform', 'url', 'is_public', 'is_active', 'icon', 'display_order']
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(link_id)
            
            db.execute(f"""
                UPDATE social_links 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, tuple(params))
            return True
        except Exception as e:
            logger.error(f"Error updating social link: {e}")
            return False
    
    def delete_social_link(self, link_id: int) -> bool:
        """Delete a social link"""
        db = self._get_db()
        
        try:
            db.execute("DELETE FROM social_links WHERE id = ?", (link_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting social link: {e}")
            return False
    
    def reorder_social_links(self, user_id: int, link_order: List[int]) -> bool:
        """Reorder social links for a user"""
        db = self._get_db()
        
        try:
            for index, link_id in enumerate(link_order):
                db.execute("""
                    UPDATE social_links 
                    SET display_order = ?
                    WHERE id = ? AND user_id = ?
                """, (index, link_id, user_id))
            return True
        except Exception as e:
            logger.error(f"Error reordering social links: {e}")
            return False
    
    # =========================================================================
    # USER ACTIVITY LOG OPERATIONS
    # =========================================================================
    
    def log_user_activity(self, user_id: int, action: str, details: str = None,
                         ip_address: str = None, user_agent: str = None) -> bool:
        """Log user activity"""
        db = self._get_db()
        
        try:
            db.execute("""
                INSERT INTO user_activity_log 
                (user_id, action, details, ip_address, user_agent, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, action, details, ip_address, user_agent, datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return False
    
    def get_user_activities(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user activity log"""
        db = self._get_db()
        
        return db.query("""
            SELECT id, action, details, ip_address, user_agent, created_at
            FROM user_activity_log
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
    
    def get_user_activity_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user activity statistics"""
        db = self._get_db()
        
        # Total activities
        total_result = db.query_one("""
            SELECT COUNT(*) as total_activities
            FROM user_activity_log 
            WHERE user_id = ?
        """, (user_id,))
        
        # Activities by action
        by_action = db.query("""
            SELECT action, COUNT(*) as count
            FROM user_activity_log 
            WHERE user_id = ?
            GROUP BY action
            ORDER BY count DESC
        """, (user_id,))
        
        # Last 7 days activity
        weekly = db.query("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM user_activity_log 
            WHERE user_id = ? 
            AND created_at >= date('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (user_id,))
        
        return {
            'total': total_result.get('total_activities', 0) if total_result else 0,
            'by_action': by_action,
            'weekly': weekly
        }
    
    # =========================================================================
    # ROLE & PERMISSION OPERATIONS
    # =========================================================================
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """
        Get all roles with their permissions
        Uses the role_permissions table for detailed permissions
        """
        db = self._get_db()
        
        try:
            # Try to get from role_permissions table first (more detailed)
            result = db.query("""
                SELECT id, role, permissions, created_at, updated_at
                FROM role_permissions
                ORDER BY 
                    CASE 
                        WHEN role = 'admin' THEN 1
                        WHEN role = 'system_admin' THEN 2
                        WHEN role = 'company_admin' THEN 3
                        WHEN role = 'manager' THEN 4
                        WHEN role = 'company_manager' THEN 5
                        WHEN role = 'analyst' THEN 6
                        WHEN role = 'viewer' THEN 7
                        WHEN role = 'system_support' THEN 8
                        WHEN role = 'system_auditor' THEN 9
                        ELSE 10
                    END
            """)
            
            if result and len(result) > 0:
                roles_list = []
                for row in result:
                    # Parse permissions if it's a string
                    permissions = row.get('permissions')
                    if isinstance(permissions, str):
                        try:
                            import json
                            permissions = json.loads(permissions)
                        except:
                            permissions = {}
                    
                    roles_list.append({
                        'id': row.get('id'),
                        'role': row.get('role'),
                        'role_name': row.get('role'),  # For compatibility
                        'permissions': permissions,
                        'created_at': row.get('created_at'),
                        'updated_at': row.get('updated_at')
                    })
                
                return roles_list
        except Exception as e:
            print(f"Error getting roles from role_permissions: {e}")
        
        # Fallback: Get from user_roles table
        try:
            result = db.query("""
                SELECT id, role_name, permissions, created_at, updated_at
                FROM user_roles
                ORDER BY id
            """)
            
            if result and len(result) > 0:
                roles_list = []
                for row in result:
                    # Parse permissions if it's a string
                    permissions = row.get('permissions')
                    if isinstance(permissions, str):
                        try:
                            import json
                            permissions = json.loads(permissions)
                        except:
                            permissions = {}
                    
                    roles_list.append({
                        'id': row.get('id'),
                        'role': row.get('role_name'),
                        'role_name': row.get('role_name'),
                        'permissions': permissions,
                        'created_at': row.get('created_at'),
                        'updated_at': row.get('updated_at')
                    })
                
                return roles_list
        except Exception as e:
            print(f"Error getting roles from user_roles: {e}")
    
        # If all fails, return default roles
        return self._get_default_roles()

    def get_role_permissions(self, role_name: str) -> Dict[str, Any]:
        """Get permissions for a role from role_permissions table"""
        db = self._get_db()
        
        # Try to get from role_permissions table
        try:
            result = db.query_one("""
                SELECT permissions FROM role_permissions 
                WHERE role = ?
            """, (role_name,))
            
            if result:
                permissions = result.get('permissions')
                if isinstance(permissions, dict):
                    return permissions
                elif isinstance(permissions, str):
                    try:
                        import json
                        return json.loads(permissions)
                    except:
                        pass
        except Exception as e:
            print(f"Error getting role permissions: {e}")
        
        # Try user_roles table
        try:
            result = db.query_one("""
                SELECT permissions FROM user_roles 
                WHERE role_name = ?
            """, (role_name,))
            
            if result:
                permissions = result.get('permissions')
                if isinstance(permissions, dict):
                    return permissions
                elif isinstance(permissions, str):
                    try:
                        import json
                        return json.loads(permissions)
                    except:
                        pass
        except Exception as e:
            print(f"Error getting role permissions from user_roles: {e}")
        
        # Return default permissions
        return self._get_default_permissions(role_name)

    def _get_default_roles(self):
        """Get default roles"""
        return [
            {'id': 1, 'role': 'admin', 'role_name': 'admin', 'permissions': {}},
            {'id': 2, 'role': 'system_admin', 'role_name': 'system_admin', 'permissions': {}},
            {'id': 3, 'role': 'company_admin', 'role_name': 'company_admin', 'permissions': {}},
            {'id': 4, 'role': 'manager', 'role_name': 'manager', 'permissions': {}},
            {'id': 5, 'role': 'company_manager', 'role_name': 'company_manager', 'permissions': {}},
            {'id': 6, 'role': 'analyst', 'role_name': 'analyst', 'permissions': {}},
            {'id': 7, 'role': 'viewer', 'role_name': 'viewer', 'permissions': {}},
            {'id': 8, 'role': 'system_support', 'role_name': 'system_support', 'permissions': {}},
            {'id': 9, 'role': 'system_auditor', 'role_name': 'system_auditor', 'permissions': {}}
        ]

    def _get_default_permissions(self, role_name: str) -> Dict[str, Any]:
        """Get default permissions for a role"""
        default_perms = {
            'viewer': {
                'manage_users': False, 'manage_tenders': False, 'run_analysis': False,
                'view_reports': True, 'export_data': False, 'change_plans': False,
                'manage_team': False, 'delete_any': False,
                'view_rates': True, 'edit_rates': False, 'delete_rates': False,
                'manage_zones': False, 'manage_chapters': False,
                'manage_parents': False, 'manage_children': False, 'manage_versions': False
            },
            'analyst': {
                'manage_users': False, 'manage_tenders': False, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': False,
                'manage_team': False, 'delete_any': False,
                'view_rates': True, 'edit_rates': False, 'delete_rates': False,
                'manage_zones': False, 'manage_chapters': False,
                'manage_parents': False, 'manage_children': False, 'manage_versions': False
            },
            'manager': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': False,
                'manage_team': True, 'delete_any': False,
                'view_rates': True, 'edit_rates': True, 'delete_rates': False,
                'manage_zones': False, 'manage_chapters': False,
                'manage_parents': False, 'manage_children': False, 'manage_versions': False
            },
            'company_admin': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': False,
                'manage_team': True, 'delete_any': False,
                'view_rates': True, 'edit_rates': True, 'delete_rates': True,
                'manage_zones': True, 'manage_chapters': True,
                'manage_parents': True, 'manage_children': True, 'manage_versions': True
            },
            'admin': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': True,
                'manage_team': True, 'delete_any': True,
                'view_rates': True, 'edit_rates': True, 'delete_rates': True,
                'manage_zones': True, 'manage_chapters': True,
                'manage_parents': True, 'manage_children': True, 'manage_versions': True
            }
        }
        
        return default_perms.get(role_name, default_perms['viewer'])
    
    def update_role_permissions(self, role_name: str, permissions: Dict[str, Any]) -> bool:
        """Update role permissions in role_permissions table"""
        db = self._get_db()
        
        try:
            # Check if role exists in role_permissions
            existing = db.query_one(
                "SELECT id FROM role_permissions WHERE role = ?",
                (role_name,)
            )
            
            if existing:
                # Update existing
                db.execute("""
                    UPDATE role_permissions
                    SET permissions = ?, updated_at = ?
                    WHERE role = ?
                """, (permissions, datetime.now().isoformat(), role_name))
            else:
                # Insert new
                db.execute("""
                    INSERT INTO role_permissions (role, permissions, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (role_name, permissions, datetime.now().isoformat(), datetime.now().isoformat()))
            
            # Also update user_roles table if it exists
            try:
                existing_ur = db.query_one(
                    "SELECT id FROM user_roles WHERE role_name = ?",
                    (role_name,)
                )
                
                if existing_ur:
                    db.execute("""
                        UPDATE user_roles
                        SET permissions = ?, updated_at = ?
                        WHERE role_name = ?
                    """, (permissions, datetime.now().isoformat(), role_name))
            except:
                pass  # user_roles table might not exist
            
            return True
        except Exception as e:
            print(f"Error updating role permissions: {e}")
            return False
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _normalize_mobile(self, mobile: str) -> str:
        """Normalize Bangladeshi mobile number"""
        # Remove any non-digit characters
        mobile = re.sub(r'\D', '', mobile)
        
        # If starts with 0, remove it
        if mobile.startswith('0'):
            mobile = mobile[1:]
        
        # If starts with 88, remove it
        if mobile.startswith('88'):
            mobile = mobile[2:]
        
        # Should be 10 digits (01XXXXXXXXX)
        if len(mobile) == 10:
            return f"0{mobile}"
        
        return mobile
    
    def validate_bangladesh_mobile(self, mobile: str) -> bool:
        """Validate Bangladeshi mobile number"""
        mobile = self._normalize_mobile(mobile)
        # Pattern: 01 followed by 9 digits (total 11 digits)
        return bool(re.match(r'^01\d{9}$', mobile))
    
    # database/crud_operations.py - Add these OTP methods

    def invalidate_old_otps(self, contact_type: str, contact_value: str, purpose: str) -> bool:
        """Invalidate old unused OTPs"""
        try:
            self.execute("""
                UPDATE otp_verification
                SET is_used = 1
                WHERE contact_type = ? AND contact_value = ? AND purpose = ? AND is_used = 0
            """, (contact_type, contact_value, purpose))
            return True
        except Exception as e:
            print(f"Error invalidating OTPs: {e}")
            return False

    def create_otp(self, data: Dict) -> int:
        """Create a new OTP record using direct Supabase client"""
        try:
            # ✅ If using Supabase, use direct client
            if self._use_supabase and hasattr(self, 'supabase') and self.supabase:
                response = self.supabase.table('otp_verification').insert({
                    'target_type': data.get('target_type'),
                    'target_id': data.get('target_id'),
                    'contact_type': data.get('contact_type'),
                    'contact_value': data.get('contact_value'),
                    'otp_code': data.get('otp_code'),
                    'purpose': data.get('purpose'),
                    'expires_at': data.get('expires_at'),
                    'created_at': datetime.now().isoformat()
                }).execute()
                
                if response.data:
                    return response.data[0].get('id')
                return None
            else:
                # SQLite fallback
                self.execute("""
                    INSERT INTO otp_verification 
                    (target_type, target_id, contact_type, contact_value, 
                    otp_code, purpose, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('target_type'),
                    data.get('target_id'),
                    data.get('contact_type'),
                    data.get('contact_value'),
                    data.get('otp_code'),
                    data.get('purpose'),
                    data.get('expires_at'),
                    datetime.now().isoformat()
                ))
                
                result = self.query_one("SELECT last_insert_rowid() as id")
                return result.get('id') if result else None
                
        except Exception as e:
            print(f"Error creating OTP: {e}")
            return None
    
    def get_valid_otp(self, contact_type: str, contact_value: str, otp_code: str, 
                    purpose: str, max_attempts: int) -> Optional[Dict]:
        """Get a valid OTP record"""
        try:
            return self.query_one("""
                SELECT * FROM otp_verification
                WHERE contact_type = ? 
                AND contact_value = ?
                AND otp_code = ?
                AND purpose = ?
                AND is_used = 0
                AND expires_at > CURRENT_TIMESTAMP
                AND attempts < ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (contact_type, contact_value, otp_code, purpose, max_attempts))
        except Exception as e:
            print(f"Error getting valid OTP: {e}")
            return None

    def get_latest_otp(self, contact_value: str, purpose: str) -> Optional[Dict]:
        """Get the latest OTP for a contact"""
        try:
            return self.query_one("""
                SELECT * FROM otp_verification
                WHERE contact_value = ? AND purpose = ?
                ORDER BY created_at DESC LIMIT 1
            """, (contact_value, purpose))
        except Exception as e:
            print(f"Error getting latest OTP: {e}")
            return None

    def increment_otp_attempts(self, contact_type: str, contact_value: str, purpose: str) -> bool:
        """Increment attempts for the latest OTP"""
        try:
            self.execute("""
                UPDATE otp_verification
                SET attempts = attempts + 1
                WHERE contact_type = ? AND contact_value = ? AND purpose = ? AND is_used = 0
            """, (contact_type, contact_value, purpose))
            return True
        except Exception as e:
            print(f"Error incrementing OTP attempts: {e}")
            return False

    def mark_otp_used(self, otp_id: int) -> bool:
        """Mark OTP as used"""
        try:
            self.execute("""
                UPDATE otp_verification
                SET is_used = 1, used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (otp_id,))
            return True
        except Exception as e:
            print(f"Error marking OTP used: {e}")
            return False

    def update_verification_status(self, table: str, target_id: int, updates: Dict) -> bool:
        """Update verification status in target table"""
        try:
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [target_id]
            
            self.execute(f"""
                UPDATE {table}
                SET {set_clause}
                WHERE id = ?
            """, values)
            return True
        except Exception as e:
            print(f"Error updating verification status: {e}")
            return False

    def log_verification_history(self, target_type: str, target_id: int, 
                                contact_type: str, contact_value: str, 
                                method: str) -> bool:
        """Log verification history"""
        try:
            self.execute("""
                INSERT INTO verification_history
                (target_type, target_id, contact_type, contact_value, verification_method, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (target_type, target_id, contact_type, contact_value, method, datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"Error logging verification history: {e}")
            return False