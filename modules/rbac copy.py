# modules/rbac.py (UPDATED)

import streamlit as st
from typing import Dict, List, Any, Optional
from functools import wraps

from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()

# =============================================================================
# ROLE DEFINITIONS AND PERMISSIONS
# =============================================================================

ROLE_PERMISSIONS: Dict[str, Dict[str, bool]] = {
    # System Admin - Full access to everything
    'system_admin': {
        
        # ========== Scenario Generator Permissions ==========
        'can_access_scenario_generator': True,
        'can_generate_scenarios': True,
        'can_export_scenarios': True,
        
        # ========== Rate Management Permissions ==========
        # System-level master rates (PWD, LGED)
        'can_view_system_rates': True,
        'can_edit_system_rates': True,
        'can_delete_system_rates': True,
        'can_import_system_rates': True,
        'can_export_system_rates': True,
        
        # Tenant-level rate books
        'can_view_tenant_rates': True,
        'can_create_rate_book': True,
        'can_edit_tenant_rates': True,
        'can_delete_tenant_rates': True,
        'can_import_tenant_rates': True,
        'can_export_tenant_rates': True,
        'can_clone_master_rates': True,
        'can_create_rate_version': True,
        'can_archive_rate_book': True,
        'can_manage_rate_books': True,
        'can_view_all_tenant_rates': True,
        
        # ========== Original Rate Permissions (Legacy) ==========
        'can_view_rates': True,
        'can_edit_rates': True,
        'can_delete_rates': True,
        'can_create_versions': True,
        'can_import_rates': True,
        'can_export_data': True,
        
        # ========== Tender Management ==========
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_delete_tender': True,
        'can_submit_bid': True,
        'can_manage_team': True,
        'can_lock_tender': True,
        
        # ========== BOQ Management ==========
        'can_view_boq': True,
        'can_create_boq': True,
        'can_edit_boq': True,
        'can_delete_boq': True,
        
        # ========== Analysis & Optimization ==========
        'can_run_analysis': True,
        'can_optimize_bid': True,
        'can_view_reports': True,
        
        # ========== Competitor Tracking ==========
        'can_view_competitors': True,
        'can_edit_competitors': True,
        'can_delete_competitors': True,
        
        # ========== User & Company Management ==========
        'can_manage_users': True,
        'can_manage_companies': True,
        'can_view_all_companies': True,
        'can_manage_subscriptions': True,
        'can_approve_users': True,
        'can_manage_roles': True,
        
        # ========== System ==========
        'can_view_audit_logs': True,
        'can_manage_system': True,
        
        # ========== General ==========
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': True,

        # ========== Extension ==========
        'can_use_extension': True,
        'can_view_extension_usage': True,
    },
    
    # Admin - Full access to own company
    'admin': {
        # ========== Rate Management Permissions ==========
        'can_view_system_rates': True,
        'can_edit_system_rates': False,
        'can_delete_system_rates': False,
        'can_import_system_rates': False,
        'can_export_system_rates': True,
        
        'can_view_tenant_rates': True,
        'can_create_rate_book': True,
        'can_edit_tenant_rates': True,
        'can_delete_tenant_rates': True,
        'can_import_tenant_rates': True,
        'can_export_tenant_rates': True,
        'can_clone_master_rates': True,
        'can_create_rate_version': True,
        'can_archive_rate_book': True,
        'can_manage_rate_books': True,
        'can_view_all_tenant_rates': False,
        
        # Legacy
        'can_view_rates': True,
        'can_edit_rates': True,
        'can_delete_rates': True,
        'can_create_versions': True,
        'can_import_rates': True,
        'can_export_data': True,
        
        # Other permissions
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_delete_tender': True,
        'can_submit_bid': True,
        'can_manage_team': True,
        'can_lock_tender': True,
        'can_view_boq': True,
        'can_create_boq': True,
        'can_edit_boq': True,
        'can_delete_boq': True,
        'can_run_analysis': True,
        'can_optimize_bid': True,
        'can_view_reports': True,
        'can_view_competitors': True,
        'can_edit_competitors': True,
        'can_delete_competitors': True,
        'can_manage_users': True,
        'can_manage_companies': True,
        'can_view_all_companies': False,
        'can_manage_subscriptions': True,
        'can_approve_users': True,
        'can_manage_roles': False,
        'can_view_audit_logs': True,
        'can_manage_system': False,
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': True,
        'can_use_extension': True,
        'can_view_extension_usage': True,
        'can_access_scenario_generator': True,
        'can_generate_scenarios': True,
        'can_export_scenarios': True,
    },
    
    # Company Admin - Full access to own company's data
    'company_admin': {
        # ========== Rate Management Permissions ==========
        'can_view_system_rates': True,
        'can_edit_system_rates': False,
        'can_delete_system_rates': False,
        'can_import_system_rates': False,
        'can_export_system_rates': True,
        
        'can_view_tenant_rates': True,
        'can_create_rate_book': True,
        'can_edit_tenant_rates': True,
        'can_delete_tenant_rates': True,
        'can_import_tenant_rates': True,
        'can_export_tenant_rates': True,
        'can_clone_master_rates': True,
        'can_create_rate_version': True,
        'can_archive_rate_book': True,
        'can_manage_rate_books': True,
        'can_view_all_tenant_rates': False,
        
        # Legacy
        'can_view_rates': True,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_import_rates': False,
        'can_export_data': True,
        
        # Other permissions
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_delete_tender': True,
        'can_submit_bid': True,
        'can_manage_team': True,
        'can_lock_tender': True,
        'can_view_boq': True,
        'can_create_boq': True,
        'can_edit_boq': True,
        'can_delete_boq': True,
        'can_run_analysis': True,
        'can_optimize_bid': True,
        'can_view_reports': True,
        'can_view_competitors': True,
        'can_edit_competitors': True,
        'can_delete_competitors': False,
        'can_manage_users': True,
        'can_manage_companies': False,
        'can_view_all_companies': False,
        'can_manage_subscriptions': True,
        'can_approve_users': False,
        'can_manage_roles': False,
        'can_view_audit_logs': False,
        'can_manage_system': False,
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': True,
        'can_access_scenario_generator': True,
        'can_generate_scenarios': True,
        'can_export_scenarios': True,
        'can_use_extension': True,
        'can_view_extension_usage': True,
    },
    
    # Manager - Operational access
    'manager': {
        # ========== Rate Management Permissions ==========
        'can_view_system_rates': True,
        'can_edit_system_rates': False,
        'can_delete_system_rates': False,
        'can_import_system_rates': False,
        'can_export_system_rates': True,
        
        'can_view_tenant_rates': True,
        'can_create_rate_book': True,
        'can_edit_tenant_rates': True,
        'can_delete_tenant_rates': False,
        'can_import_tenant_rates': True,
        'can_export_tenant_rates': True,
        'can_clone_master_rates': True,
        'can_create_rate_version': True,
        'can_archive_rate_book': False,
        'can_manage_rate_books': True,
        'can_view_all_tenant_rates': False,
        
        # Legacy
        'can_view_rates': True,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_import_rates': False,
        'can_export_data': True,
        
        # Other permissions
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_delete_tender': False,
        'can_submit_bid': True,
        'can_manage_team': True,
        'can_lock_tender': False,
        'can_view_boq': True,
        'can_create_boq': True,
        'can_edit_boq': True,
        'can_delete_boq': False,
        'can_run_analysis': True,
        'can_optimize_bid': True,
        'can_view_reports': True,
        'can_view_competitors': True,
        'can_edit_competitors': True,
        'can_delete_competitors': False,
        'can_manage_users': False,
        'can_manage_companies': False,
        'can_view_all_companies': False,
        'can_manage_subscriptions': False,
        'can_approve_users': False,
        'can_manage_roles': False,
        'can_view_audit_logs': False,
        'can_manage_system': False,
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': False,
        'can_access_scenario_generator': True,
        'can_generate_scenarios': True,
        'can_export_scenarios': True,
        'can_use_extension': True,
        'can_view_extension_usage': True,
    },
    
    # Analyst - Can run analysis and create BOQ
    'analyst': {
        # ========== Rate Management Permissions ==========
        'can_view_system_rates': True,
        'can_edit_system_rates': False,
        'can_delete_system_rates': False,
        'can_import_system_rates': False,
        'can_export_system_rates': True,
        
        'can_view_tenant_rates': True,
        'can_create_rate_book': False,
        'can_edit_tenant_rates': False,
        'can_delete_tenant_rates': False,
        'can_import_tenant_rates': False,
        'can_export_tenant_rates': True,
        'can_clone_master_rates': False,
        'can_create_rate_version': False,
        'can_archive_rate_book': False,
        'can_manage_rate_books': False,
        'can_view_all_tenant_rates': False,
        
        # Legacy
        'can_view_rates': True,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_import_rates': False,
        'can_export_data': True,
        
        # Other permissions
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_delete_tender': False,
        'can_submit_bid': True,
        'can_manage_team': False,
        'can_lock_tender': False,
        'can_view_boq': True,
        'can_create_boq': True,
        'can_edit_boq': True,
        'can_delete_boq': False,
        'can_run_analysis': True,
        'can_optimize_bid': True,
        'can_view_reports': True,
        'can_view_competitors': True,
        'can_edit_competitors': False,
        'can_delete_competitors': False,
        'can_manage_users': False,
        'can_manage_companies': False,
        'can_view_all_companies': False,
        'can_manage_subscriptions': False,
        'can_approve_users': False,
        'can_manage_roles': False,
        'can_view_audit_logs': False,
        'can_manage_system': False,
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': False,
        'can_access_scenario_generator': True,
        'can_generate_scenarios': True,
        'can_export_scenarios': True,
        'can_use_extension': True,
        'can_view_extension_usage': True,
    },
    
    # Data Entry - Can enter data but not run analysis
    'data_entry': {
        # ========== Rate Management Permissions ==========
        'can_view_system_rates': True,
        'can_edit_system_rates': False,
        'can_delete_system_rates': False,
        'can_import_system_rates': False,
        'can_export_system_rates': False,
        
        'can_view_tenant_rates': True,
        'can_create_rate_book': False,
        'can_edit_tenant_rates': False,
        'can_delete_tenant_rates': False,
        'can_import_tenant_rates': False,
        'can_export_tenant_rates': False,
        'can_clone_master_rates': False,
        'can_create_rate_version': False,
        'can_archive_rate_book': False,
        'can_manage_rate_books': False,
        'can_view_all_tenant_rates': False,
        
        # Legacy
        'can_view_rates': True,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_import_rates': False,
        'can_export_data': False,
        
        # Other permissions
        'can_view_tenders': True,
        'can_create_tender': True,
        'can_edit_tender': True,
        'can_delete_tender': False,
        'can_submit_bid': False,
        'can_manage_team': False,
        'can_lock_tender': False,
        'can_view_boq': True,
        'can_create_boq': False,
        'can_edit_boq': False,
        'can_delete_boq': False,
        'can_run_analysis': False,
        'can_optimize_bid': False,
        'can_view_reports': True,
        'can_view_competitors': True,
        'can_edit_competitors': False,
        'can_delete_competitors': False,
        'can_manage_users': False,
        'can_manage_companies': False,
        'can_view_all_companies': False,
        'can_manage_subscriptions': False,
        'can_approve_users': False,
        'can_manage_roles': False,
        'can_view_audit_logs': False,
        'can_manage_system': False,
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': False,
        'can_access_scenario_generator': True,
        'can_generate_scenarios': False,
        'can_export_scenarios': False,
        'can_use_extension': True,
        'can_view_extension_usage': False,
    },
    
    # Viewer - Read-only access
    'viewer': {
        # ========== Rate Management Permissions ==========
        'can_view_system_rates': True,
        'can_edit_system_rates': False,
        'can_delete_system_rates': False,
        'can_import_system_rates': False,
        'can_export_system_rates': False,
        
        'can_view_tenant_rates': True,
        'can_create_rate_book': False,
        'can_edit_tenant_rates': False,
        'can_delete_tenant_rates': False,
        'can_import_tenant_rates': False,
        'can_export_tenant_rates': False,
        'can_clone_master_rates': False,
        'can_create_rate_version': False,
        'can_archive_rate_book': False,
        'can_manage_rate_books': False,
        'can_view_all_tenant_rates': False,
        
        # Legacy
        'can_view_rates': True,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_import_rates': False,
        'can_export_data': False,
        
        # Other permissions
        'can_view_tenders': True,
        'can_create_tender': False,
        'can_edit_tender': False,
        'can_delete_tender': False,
        'can_submit_bid': False,
        'can_manage_team': False,
        'can_lock_tender': False,
        'can_view_boq': True,
        'can_create_boq': False,
        'can_edit_boq': False,
        'can_delete_boq': False,
        'can_run_analysis': False,
        'can_optimize_bid': False,
        'can_view_reports': True,
        'can_view_competitors': True,
        'can_edit_competitors': False,
        'can_delete_competitors': False,
        'can_manage_users': False,
        'can_manage_companies': False,
        'can_view_all_companies': False,
        'can_manage_subscriptions': False,
        'can_approve_users': False,
        'can_manage_roles': False,
        'can_view_audit_logs': False,
        'can_manage_system': False,
        'can_view_dashboard': True,
        'can_view_profile': True,
        'can_change_settings': False,
        'can_access_scenario_generator': False,
        'can_generate_scenarios': False,
        'can_export_scenarios': False,
        'can_use_extension': False,
        'can_view_extension_usage': False,
    },
}

# =============================================================================
# NEW PERMISSION FUNCTIONS FOR RATE MANAGEMENT
# =============================================================================

# ========== System Rate Permissions ==========
def can_view_system_rates() -> bool:
    """Check if user can view system-level rates (PWD, LGED master)"""
    return _rbac.has_permission('can_view_system_rates')


def can_edit_system_rates() -> bool:
    """Check if user can edit system-level rates"""
    return _rbac.has_permission('can_edit_system_rates')


def can_delete_system_rates() -> bool:
    """Check if user can delete system-level rates"""
    return _rbac.has_permission('can_delete_system_rates')


def can_import_system_rates() -> bool:
    """Check if user can import system-level rates"""
    return _rbac.has_permission('can_import_system_rates')


def can_export_system_rates() -> bool:
    """Check if user can export system-level rates"""
    return _rbac.has_permission('can_export_system_rates')


# ========== Tenant Rate Permissions ==========
def can_view_tenant_rates() -> bool:
    """Check if user can view tenant-level rates"""
    return _rbac.has_permission('can_view_tenant_rates')


def can_create_rate_book() -> bool:
    """Check if user can create rate books"""
    return _rbac.has_permission('can_create_rate_book')


def can_edit_tenant_rates() -> bool:
    """Check if user can edit tenant-level rates"""
    return _rbac.has_permission('can_edit_tenant_rates')


def can_delete_tenant_rates() -> bool:
    """Check if user can delete tenant-level rates"""
    return _rbac.has_permission('can_delete_tenant_rates')


def can_import_tenant_rates() -> bool:
    """Check if user can import tenant-level rates"""
    return _rbac.has_permission('can_import_tenant_rates')


def can_export_tenant_rates() -> bool:
    """Check if user can export tenant-level rates"""
    return _rbac.has_permission('can_export_tenant_rates')


def can_clone_master_rates() -> bool:
    """Check if user can clone master rates to tenant rate books"""
    return _rbac.has_permission('can_clone_master_rates')


def can_create_rate_version() -> bool:
    """Check if user can create rate book versions"""
    return _rbac.has_permission('can_create_rate_version')


def can_archive_rate_book() -> bool:
    """Check if user can archive rate books"""
    return _rbac.has_permission('can_archive_rate_book')


def can_manage_rate_books() -> bool:
    """Check if user has any rate book management permission"""
    return _rbac.has_any_permission(
        'can_create_rate_book',
        'can_edit_tenant_rates',
        'can_delete_tenant_rates',
        'can_import_tenant_rates',
        'can_clone_master_rates',
        'can_create_rate_version',
        'can_archive_rate_book'
    )


def can_view_all_tenant_rates() -> bool:
    """Check if user can view all tenant rates (system admin only)"""
    return _rbac.has_permission('can_view_all_tenant_rates')


# ========== Combined Rate Access Functions ==========
def can_view_any_rates() -> bool:
    """Check if user can view any rates (system or tenant)"""
    return _rbac.has_any_permission('can_view_system_rates', 'can_view_tenant_rates')


def can_edit_any_rates() -> bool:
    """Check if user can edit any rates (system or tenant)"""
    return _rbac.has_any_permission('can_edit_system_rates', 'can_edit_tenant_rates')


def can_import_any_rates() -> bool:
    """Check if user can import any rates (system or tenant)"""
    return _rbac.has_any_permission('can_import_system_rates', 'can_import_tenant_rates')


def can_export_any_rates() -> bool:
    """Check if user can export any rates (system or tenant)"""
    return _rbac.has_any_permission('can_export_system_rates', 'can_export_tenant_rates')


def is_rate_admin() -> bool:
    """Check if user is a rate administrator (can manage both system and tenant rates)"""
    return can_edit_system_rates() or can_edit_tenant_rates()


# =============================================================================
# RBAC MANAGER CLASS - REMAINS UNCHANGED
# =============================================================================

class RBACManager:
    """Role-Based Access Control Manager"""
    
    def __init__(self):
        pass
    
    def get_current_user_role(self) -> str:
        """Get current user's role from session state (always fresh)"""
        role = st.session_state.get('user_role', 'viewer')
        
        if role == 'system_admin' and st.session_state.get('company_id'):
            try:
                from database.unified_db_manager import db
                user_id = st.session_state.get('user_id')
                if user_id:
                    user = db.get_user_by_id(user_id)
                    if user and user.get('role') == 'company_admin':
                        st.session_state.user_role = 'company_admin'
                        return 'company_admin'
            except:
                pass
        
        return role
    
    def get_current_user_permissions(self) -> Dict[str, bool]:
        """Get all permissions for current user"""
        role = self.get_current_user_role()
        return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS.get('viewer', {}))
    
    def has_permission(self, permission: str) -> bool:
        """Check if current user has a specific permission"""
        permissions = self.get_current_user_permissions()
        return permissions.get(permission, False)
    
    def has_any_permission(self, *permissions: str) -> bool:
        """Check if current user has any of the specified permissions"""
        user_perms = self.get_current_user_permissions()
        return any(user_perms.get(p, False) for p in permissions)
    
    def has_all_permissions(self, *permissions: str) -> bool:
        """Check if current user has all specified permissions"""
        user_perms = self.get_current_user_permissions()
        return all(user_perms.get(p, False) for p in permissions)
    
    def refresh_role(self) -> None:
        """Force refresh role from database"""
        user_id = st.session_state.get('user_id')
        if user_id:
            try:
                from database.unified_db_manager import db
                user = db.get_user_by_id(user_id)
                if user:
                    st.session_state.user_role = user.get('role', 'viewer')
                    print(f"🔄 Refreshed role to: {st.session_state.user_role}")
            except Exception as e:
                print(f"⚠️ Failed to refresh role: {e}")
    
    def require_permission(self, permission: str):
        """Decorator to require a permission for a function"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.has_permission(permission):
                    st.error(f"🔒 You don't have permission to perform this action. Required: {permission}")
                    return None
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def render_permission_info(self) -> None:
        """Render permission info for current user (for debugging)"""
        role = self.get_current_user_role()
        permissions = self.get_current_user_permissions()
        
        with st.expander(f"🔐 Role: {role.upper()} - Permissions", expanded=False):
            cols = st.columns(2)
            for i, (perm, value) in enumerate(permissions.items()):
                status = "✅" if value else "❌"
                with cols[i % 2]:
                    st.markdown(f"{status} {perm.replace('_', ' ').title()}")
    
    def get_accessible_pages(self) -> List[str]:
        """Get list of pages accessible to current user"""
        permissions = self.get_current_user_permissions()
        pages = ['dashboard']
        
        if permissions.get('can_view_tenders'):
            pages.append('tender_management')
        
        if permissions.get('can_view_boq'):
            pages.append('boq_generator')
        
        if permissions.get('can_optimize_bid'):
            pages.append('boq_bid_optimizer')
        
        # Rate Management pages
        if permissions.get('can_view_tenant_rates') or permissions.get('can_view_system_rates'):
            pages.append('rate_management')
            
            if permissions.get('can_manage_rate_books'):
                pages.append('my_rate_books')
            
            if permissions.get('can_create_rate_book'):
                pages.append('create_rate_book')
            
            if permissions.get('can_view_system_rates'):
                pages.append('pwd_master_rates')
                pages.append('lged_master_rates')
            
            if permissions.get('can_import_any_rates'):
                pages.append('import_rates')
            
            if permissions.get('can_export_any_rates'):
                pages.append('export_rates')
        
        if permissions.get('can_manage_users'):
            pages.append('user_management')
        
        if permissions.get('can_manage_subscriptions'):
            pages.append('subscription')
        
        if permissions.get('can_view_reports'):
            pages.append('analysis_history')
        
        if permissions.get('can_view_competitors'):
            pages.append('competitor_tracking')
            pages.append('competitor_master')
        
        if permissions.get('can_view_all_companies') or permissions.get('can_manage_roles'):
            pages.append('admin_dashboard')
        
        return pages


# =============================================================================
# GLOBAL FUNCTIONS FOR EASY ACCESS
# =============================================================================

_rbac = RBACManager()

def get_current_user_role() -> str:
    """Get current user's role"""
    return _rbac.get_current_user_role()

# ========== Legacy Rate Management Permissions (Keep for backward compatibility) ==========
def can_view_rates() -> bool:
    return _rbac.has_permission('can_view_rates')


def can_edit_rates() -> bool:
    return _rbac.has_permission('can_edit_rates')


def can_delete_rates() -> bool:
    return _rbac.has_permission('can_delete_rates')


def can_import_rates() -> bool:
    return _rbac.has_permission('can_import_rates')


def can_create_versions() -> bool:
    return _rbac.has_permission('can_create_versions')


# ========== Tender Management Permissions ==========
def can_view_tenders() -> bool:
    return _rbac.has_permission('can_view_tenders')


def can_create_tender() -> bool:
    return _rbac.has_permission('can_create_tender')


def can_edit_tender() -> bool:
    return _rbac.has_permission('can_edit_tender')


def can_delete_tender() -> bool:
    return _rbac.has_permission('can_delete_tender')


def can_submit_bid() -> bool:
    return _rbac.has_permission('can_submit_bid')


def can_manage_team() -> bool:
    return _rbac.has_permission('can_manage_team')


def can_lock_tender() -> bool:
    return _rbac.has_permission('can_lock_tender')


# ========== BOQ Management Permissions ==========
def can_view_boq() -> bool:
    return _rbac.has_permission('can_view_boq')


def can_create_boq() -> bool:
    return _rbac.has_permission('can_create_boq')


def can_edit_boq() -> bool:
    return _rbac.has_permission('can_edit_boq')


def can_delete_boq() -> bool:
    return _rbac.has_permission('can_delete_boq')


# ========== Analysis & Optimization Permissions ==========
def can_run_analysis() -> bool:
    return _rbac.has_permission('can_run_analysis')


def can_optimize_bid() -> bool:
    return _rbac.has_permission('can_optimize_bid')


def can_view_reports() -> bool:
    return _rbac.has_permission('can_view_reports')


def can_export_data() -> bool:
    return _rbac.has_permission('can_export_data')


# ========== Competitor Tracking Permissions ==========
def can_view_competitors() -> bool:
    return _rbac.has_permission('can_view_competitors')


def can_edit_competitors() -> bool:
    return _rbac.has_permission('can_edit_competitors')


def can_delete_competitors() -> bool:
    return _rbac.has_permission('can_delete_competitors')


# ========== User & Company Management Permissions ==========
def can_manage_users() -> bool:
    return _rbac.has_permission('can_manage_users')


def can_manage_companies() -> bool:
    return _rbac.has_permission('can_manage_companies')


def can_view_all_companies() -> bool:
    return _rbac.has_permission('can_view_all_companies')


def can_manage_subscriptions() -> bool:
    return _rbac.has_permission('can_manage_subscriptions')


def can_approve_users() -> bool:
    return _rbac.has_permission('can_approve_users')


def can_manage_roles() -> bool:
    return _rbac.has_permission('can_manage_roles')


# ========== System Permissions ==========
def can_view_audit_logs() -> bool:
    return _rbac.has_permission('can_view_audit_logs')


def can_manage_system() -> bool:
    return _rbac.has_permission('can_manage_system')


# ========== General Permissions ==========
def can_view_dashboard() -> bool:
    return _rbac.has_permission('can_view_dashboard')


def can_view_profile() -> bool:
    return _rbac.has_permission('can_view_profile')


def can_change_settings() -> bool:
    return _rbac.has_permission('can_change_settings')


# ========== Scenario Generator Permissions ==========
def can_access_scenario_generator() -> bool:
    return _rbac.has_permission('can_access_scenario_generator')


def can_generate_scenarios() -> bool:
    return _rbac.has_permission('can_generate_scenarios')


def can_export_scenarios() -> bool:
    return _rbac.has_permission('can_export_scenarios')


# ========== Extension Permissions ==========
def can_use_extension() -> bool:
    return _rbac.has_permission('can_use_extension')


def can_view_extension_usage() -> bool:
    return _rbac.has_permission('can_view_extension_usage')


# ========== Role Check Functions ==========
def is_admin() -> bool:
    role = _rbac.get_current_user_role()
    return role in ['admin', 'system_admin']


def is_company_admin() -> bool:
    role = _rbac.get_current_user_role()
    return role in ['admin', 'system_admin', 'company_admin']


def is_manager() -> bool:
    role = _rbac.get_current_user_role()
    return role in ['admin', 'system_admin', 'company_admin', 'manager']


def is_analyst() -> bool:
    role = _rbac.get_current_user_role()
    return role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_role_badge() -> None:
    """Render a badge showing current user's role"""
    from modules.rbac import _rbac
    
    role = _rbac.get_current_user_role()
    
    if role == 'system_admin' and st.session_state.get('company_id'):
        user_id = st.session_state.get('user_id')
        if user_id:
            user = db.get_user_by_id(user_id)
            if user and user.get('role') == 'company_admin':
                role = 'company_admin'
                st.session_state.user_role = 'company_admin'
    
    role_display = {
        'system_admin': '👑 System Administrator',
        'admin': '👑 Administrator',
        'company_admin': '🏢 Company Administrator',
        'manager': '📊 Manager',
        'analyst': '📈 Analyst',
        'data_entry': '📝 Data Entry',
        'viewer': '👁️ Viewer',
        'user': '👤 User'
    }.get(role, f'👤 {role.replace("_", " ").title()}')
    
    role_colors = {
        'system_admin': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'admin': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'company_admin': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'manager': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'analyst': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'viewer': 'linear-gradient(135deg, #a8a8a8 0%, #d3d3d3 100%)'
    }
    
    gradient = role_colors.get(role, 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)')
    
    st.markdown(f"""
    <div style="background: {gradient}; 
                border-radius: 20px; padding: 4px 15px; display: inline-block; margin-bottom: 10px;">
        <span style="color: white; font-size: 0.8rem; font-weight: 500;">{role_display}</span>
    </div>
    """, unsafe_allow_html=True)


def render_protected_button(label: str, permission: str, key: str, 
                            on_click=None, use_container_width=False,
                            button_type="secondary") -> bool:
    """Render a button only if user has permission"""
    if _rbac.has_permission(permission):
        return st.button(label, key=key, use_container_width=use_container_width, 
                        type=button_type, on_click=on_click)
    else:
        st.button(f"🔒 {label}", key=f"{key}_disabled", 
                  use_container_width=use_container_width, disabled=True,
                  help=f"Requires permission: {permission}")
    return False


def render_protected_data_editor(df, permission: str, **kwargs):
    """Render a data editor only if user has permission"""
    if _rbac.has_permission(permission):
        return st.data_editor(df, **kwargs)
    else:
        st.info("🔒 View-only mode")
        return st.dataframe(df, **kwargs)


def require_permission(permission: str):
    """Decorator to require a permission"""
    return _rbac.require_permission(permission)


# =============================================================================
# HELPER FUNCTIONS FOR MODULES
# =============================================================================

def get_user_permissions_dict() -> Dict[str, bool]:
    """Get current user's permissions as a dictionary"""
    return _rbac.get_current_user_permissions()


def get_user_role() -> str:
    """Get current user's role"""
    return _rbac.get_current_user_role()


def check_feature_access(feature: str) -> bool:
    """Check if user has access to a specific feature"""
    feature_permission_map = {
        'rate_management': 'can_edit_rates',
        'rate_book_management': 'can_manage_rate_books',
        'pwd_master_rates': 'can_view_system_rates',
        'lged_master_rates': 'can_view_system_rates',
        'tenant_rate_books': 'can_view_tenant_rates',
        'create_rate_book': 'can_create_rate_book',
        'import_rates': 'can_import_any_rates',
        'export_rates': 'can_export_any_rates',
        'boq_generation': 'can_create_boq',
        'bid_optimization': 'can_optimize_bid',
        'tender_analysis': 'can_run_analysis',
        'competitor_tracking': 'can_view_competitors',
        'export_reports': 'can_export_data',
        'team_management': 'can_manage_team',
        'subscription_management': 'can_manage_subscriptions',
    }
    
    permission = feature_permission_map.get(feature)
    if permission:
        return _rbac.has_permission(permission)
    return False


def is_premium_user(role: str = None) -> bool:
    """Check if user has premium access"""
    if role is None:
        role = _rbac.get_current_user_role()
    
    premium_roles = ['system_admin', 'admin', 'company_admin', 'manager', 'analyst']
    return role in premium_roles


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_rbac():
    """Initialize RBAC in session state"""
    if 'rbac_initialized' not in st.session_state:
        st.session_state.rbac_initialized = True
        if 'user_role' not in st.session_state:
            st.session_state.user_role = 'viewer'


# Create singleton instance
rbac = RBACManager()