"""
Role CRUD Operations
Handles role and permission management
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RoleCRUD:
    """Role-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get the database manager"""
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        elif self._db_manager:
            return self._db_manager
        else:
            from database.unified_db_manager import get_db_manager
            return get_db_manager()
    
    # ============================================================
    # ROLE OPERATIONS
    # ============================================================
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """
        Get all roles with their permissions from user_roles table
        """
        db = self._get_db()
        
        try:
            # Try Supabase first
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                response = db.supabase.table('user_roles') \
                    .select('*') \
                    .order('id') \
                    .execute()
                
                if response.data:
                    roles_list = []
                    for row in response.data:
                        permissions = row.get('permissions')
                        if isinstance(permissions, str):
                            try:
                                permissions = json.loads(permissions)
                            except:
                                permissions = {}
                        elif isinstance(permissions, dict):
                            pass  # Already a dict
                        else:
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
            
            # SQLite fallback
            result = db.query("""
                SELECT id, role_name, permissions, created_at, updated_at
                FROM user_roles
                ORDER BY 
                    CASE 
                        WHEN role_name = 'admin' THEN 1
                        WHEN role_name = 'system_admin' THEN 2
                        WHEN role_name = 'company_admin' THEN 3
                        WHEN role_name = 'manager' THEN 4
                        WHEN role_name = 'company_manager' THEN 5
                        WHEN role_name = 'analyst' THEN 6
                        WHEN role_name = 'viewer' THEN 7
                        WHEN role_name = 'individual' THEN 8
                        ELSE 10
                    END
            """)
            
            if result and len(result) > 0:
                roles_list = []
                for row in result:
                    permissions = row.get('permissions')
                    if isinstance(permissions, str):
                        try:
                            permissions = json.loads(permissions)
                        except:
                            permissions = {}
                    elif isinstance(permissions, dict):
                        pass
                    else:
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
            
            # If no data, return default roles
            return self._get_default_roles()
            
        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            return self._get_default_roles()
    
    def get_role_by_name(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific role by name"""
        db = self._get_db()
        
        try:
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                response = db.supabase.table('user_roles') \
                    .select('*') \
                    .eq('role_name', role_name) \
                    .execute()
                
                if response.data:
                    row = response.data[0]
                    permissions = row.get('permissions')
                    if isinstance(permissions, str):
                        try:
                            permissions = json.loads(permissions)
                        except:
                            permissions = {}
                    
                    return {
                        'id': row.get('id'),
                        'role': row.get('role_name'),
                        'role_name': row.get('role_name'),
                        'permissions': permissions,
                        'created_at': row.get('created_at'),
                        'updated_at': row.get('updated_at')
                    }
            
            result = db.query_one(
                "SELECT id, role_name, permissions, created_at, updated_at FROM user_roles WHERE role_name = ?",
                (role_name,)
            )
            
            if result:
                permissions = result.get('permissions')
                if isinstance(permissions, str):
                    try:
                        permissions = json.loads(permissions)
                    except:
                        permissions = {}
                
                return {
                    'id': result.get('id'),
                    'role': result.get('role_name'),
                    'role_name': result.get('role_name'),
                    'permissions': permissions,
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting role {role_name}: {e}")
            return None
    
    def get_role_permissions(self, role_name: str) -> Dict[str, Any]:
        """Get permissions for a specific role"""
        role = self.get_role_by_name(role_name)
        if role:
            return role.get('permissions', {})
        return self._get_default_permissions(role_name)
    
    def create_role(self, role_name: str, permissions: Dict[str, Any], description: str = None) -> bool:
        """Create a new role"""
        db = self._get_db()
        
        try:
            # Check if role already exists
            existing = self.get_role_by_name(role_name)
            if existing:
                return False
            
            # Convert permissions to JSON string
            permissions_json = json.dumps(permissions) if permissions else '{}'
            
            # Add description to permissions if provided
            if description:
                permissions['description'] = description
                permissions_json = json.dumps(permissions)
            
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                response = db.supabase.table('user_roles') \
                    .insert({
                        'role_name': role_name,
                        'permissions': permissions_json,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }) \
                    .execute()
                
                return bool(response.data)
            
            # SQLite fallback
            result = db.execute("""
                INSERT INTO user_roles (role_name, permissions, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (role_name, permissions_json, datetime.now().isoformat(), datetime.now().isoformat()))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error creating role {role_name}: {e}")
            return False
    
    def update_role_permissions(self, role_name: str, permissions: Dict[str, Any]) -> bool:
        """Update role permissions"""
        db = self._get_db()
        
        try:
            # Check if role exists
            existing = self.get_role_by_name(role_name)
            if not existing:
                return False
            
            # Convert permissions to JSON string
            permissions_json = json.dumps(permissions) if permissions else '{}'
            
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                response = db.supabase.table('user_roles') \
                    .update({
                        'permissions': permissions_json,
                        'updated_at': datetime.now().isoformat()
                    }) \
                    .eq('role_name', role_name) \
                    .execute()
                
                return bool(response.data)
            
            # SQLite fallback
            result = db.execute("""
                UPDATE user_roles 
                SET permissions = ?, updated_at = ?
                WHERE role_name = ?
            """, (permissions_json, datetime.now().isoformat(), role_name))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error updating role permissions for {role_name}: {e}")
            return False
    
    def delete_role(self, role_name: str) -> bool:
        """Delete a role (only if not a system role)"""
        db = self._get_db()
        
        # System roles cannot be deleted
        system_roles = ['admin', 'system_admin', 'company_admin', 'manager', 'company_manager', 'analyst', 'viewer']
        if role_name in system_roles:
            return False
        
        try:
            # Check if any users have this role
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                user_response = db.supabase.table('users') \
                    .select('id') \
                    .eq('role', role_name) \
                    .limit(1) \
                    .execute()
                
                if user_response.data:
                    return False  # Users have this role
            
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                response = db.supabase.table('user_roles') \
                    .delete() \
                    .eq('role_name', role_name) \
                    .execute()
                
                return bool(response.data)
            
            # SQLite fallback
            # Check if any users have this role
            user_check = db.query_one(
                "SELECT id FROM users WHERE role = ? LIMIT 1",
                (role_name,)
            )
            if user_check:
                return False
            
            result = db.execute(
                "DELETE FROM user_roles WHERE role_name = ?",
                (role_name,)
            )
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting role {role_name}: {e}")
            return False
    
    def role_has_permission(self, role_name: str, permission: str) -> bool:
        """Check if a role has a specific permission"""
        permissions = self.get_role_permissions(role_name)
        return permissions.get(permission, False)
    
    def get_users_with_role(self, role_name: str) -> List[Dict[str, Any]]:
        """Get all users with a specific role"""
        db = self._get_db()
        
        try:
            if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                response = db.supabase.table('users') \
                    .select('id, username, email, full_name, is_active') \
                    .eq('role', role_name) \
                    .execute()
                
                return response.data if response.data else []
            
            results = db.query("""
                SELECT id, username, email, full_name, is_active
                FROM users
                WHERE role = ?
                ORDER BY full_name
            """, (role_name,))
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"Error getting users with role {role_name}: {e}")
            return []
    
    # ============================================================
    # DEFAULT ROLES & PERMISSIONS
    # ============================================================
    
    def _get_default_roles(self) -> List[Dict[str, Any]]:
        """Get default roles with permissions"""
        return [
            {
                'id': 1,
                'role': 'admin',
                'role_name': 'admin',
                'permissions': self._get_default_permissions('admin'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 2,
                'role': 'company_admin',
                'role_name': 'company_admin',
                'permissions': self._get_default_permissions('company_admin'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 3,
                'role': 'manager',
                'role_name': 'manager',
                'permissions': self._get_default_permissions('manager'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 4,
                'role': 'analyst',
                'role_name': 'analyst',
                'permissions': self._get_default_permissions('analyst'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 5,
                'role': 'viewer',
                'role_name': 'viewer',
                'permissions': self._get_default_permissions('viewer'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 6,
                'role': 'individual',
                'role_name': 'individual',
                'permissions': self._get_default_permissions('individual'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
    
    def _get_default_permissions(self, role_name: str) -> Dict[str, Any]:
        """Get default permissions for a role"""
        default_perms = {
            'viewer': {
                'manage_users': False,
                'manage_tenders': False,
                'run_analysis': False,
                'view_reports': True,
                'export_data': False,
                'change_plans': False,
                'manage_team': False,
                'delete_any': False,
                'view_rates': True,
                'edit_rates': False,
                'delete_rates': False,
                'manage_zones': False,
                'manage_chapters': False,
                'manage_parents': False,
                'manage_children': False,
                'manage_versions': False,
                'can_create_user': False,
                'can_delete_user': False,
                'can_manage_tenders': False,
                'can_manage_company_users': False,
                'can_edit_company_settings': False,
                'can_view_company_analyses': False,
                'can_manage_company_subscription': False,
                'description': 'Read-only access'
            },
            'analyst': {
                'manage_users': False,
                'manage_tenders': False,
                'run_analysis': True,
                'view_reports': True,
                'export_data': True,
                'change_plans': False,
                'manage_team': False,
                'delete_any': False,
                'view_rates': True,
                'edit_rates': False,
                'delete_rates': False,
                'manage_zones': False,
                'manage_chapters': False,
                'manage_parents': False,
                'manage_children': False,
                'manage_versions': False,
                'can_create_user': False,
                'can_delete_user': False,
                'can_manage_tenders': False,
                'can_manage_company_users': False,
                'can_edit_company_settings': False,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'description': 'Can run analyses and view reports'
            },
            'manager': {
                'manage_users': True,
                'manage_tenders': True,
                'run_analysis': True,
                'view_reports': True,
                'export_data': True,
                'change_plans': False,
                'manage_team': True,
                'delete_any': False,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': False,
                'manage_zones': False,
                'manage_chapters': False,
                'manage_parents': False,
                'manage_children': False,
                'manage_versions': False,
                'can_create_user': True,
                'can_delete_user': False,
                'can_manage_tenders': True,
                'can_manage_company_users': True,
                'can_edit_company_settings': False,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'description': 'Can manage tenders and create users'
            },
            'company_admin': {
                'manage_users': True,
                'manage_tenders': True,
                'run_analysis': True,
                'view_reports': True,
                'export_data': True,
                'change_plans': False,
                'manage_team': True,
                'delete_any': False,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': True,
                'manage_zones': True,
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': True,
                'can_create_user': True,
                'can_delete_user': True,
                'can_manage_tenders': True,
                'can_manage_company_users': True,
                'can_edit_company_settings': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': True,
                'description': 'Full company management'
            },
            'admin': {
                'manage_users': True,
                'manage_tenders': True,
                'run_analysis': True,
                'view_reports': True,
                'export_data': True,
                'change_plans': True,
                'manage_team': True,
                'delete_any': True,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': True,
                'manage_zones': True,
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': True,
                'can_create_user': True,
                'can_delete_user': True,
                'can_manage_tenders': True,
                'can_manage_company_users': True,
                'can_edit_company_settings': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': True,
                'description': 'Full platform access'
            },
            'individual': {
                'manage_users': True,
                'manage_tenders': True,
                'run_analysis': True,
                'view_reports': True,
                'export_data': True,
                'change_plans': False,
                'manage_team': True,
                'delete_any': False,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': False,
                'manage_zones': False,
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': True,
                'can_create_user': True,
                'can_delete_user': True,
                'can_manage_tenders': True,
                'can_manage_company_users': True,
                'can_edit_company_settings': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': True,
                'description': 'Full company management for individual users'
            }
        }
        
        return default_perms.get(role_name, default_perms['viewer'])
    
    # ============================================================
    # INITIALIZATION
    # ============================================================
    
    def initialize_default_roles(self) -> bool:
        """Initialize default roles if they don't exist"""
        db = self._get_db()
        
        try:
            # Check if roles already exist
            existing = self.get_all_roles()
            if existing and len(existing) > 0:
                return True
            
            # Create default roles
            default_roles = self._get_default_roles()
            for role in default_roles:
                role_name = role.get('role_name')
                permissions = role.get('permissions')
                
                # Convert permissions to JSON string for storage
                permissions_json = json.dumps(permissions) if permissions else '{}'
                
                if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
                    db.supabase.table('user_roles') \
                        .insert({
                            'role_name': role_name,
                            'permissions': permissions_json,
                            'created_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }) \
                        .execute()
                else:
                    db.execute("""
                        INSERT OR IGNORE INTO user_roles (role_name, permissions, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (role_name, permissions_json, datetime.now().isoformat(), datetime.now().isoformat()))
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing default roles: {e}")
            return False