# modules/access_control.py
"""
Unified Access Control System
Combines RBAC permissions, subscription plans, and feature limits
"""

import streamlit as st
from typing import Dict, Tuple, Optional, List
from functools import wraps

from database.unified_db_manager import db
from modules.rbac import _rbac, ROLE_PERMISSIONS
from modules.subscription_manager import SubscriptionManager, check_subscription_access, PLANS
from modules.subscription import get_plans, get_plan, is_premium_plan



# =============================================================================
# FEATURE TO PLAN MAPPING (What plan unlocks what feature)
# =============================================================================

FEATURE_PLAN_REQUIREMENTS = {
    # Premium features that require specific plans
    'can_optimize_bid': ['professional', 'enterprise'],
    'can_export_data': ['basic', 'professional', 'enterprise'],
    'can_edit_rates': ['professional', 'enterprise'],
    'can_delete_rates': ['enterprise'],
    'can_create_versions': ['professional', 'enterprise'],
    'can_manage_team': ['professional', 'enterprise'],
    'can_use_extension': ['basic', 'professional', 'enterprise'],
    'can_import_rates': ['professional', 'enterprise'],
    'can_manage_subscriptions': ['professional', 'enterprise'],
    
    # Features available on all plans
    'can_view_rates': ['free', 'basic', 'professional', 'enterprise'],
    'can_view_tenders': ['free', 'basic', 'professional', 'enterprise'],
    'can_create_tender': ['free', 'basic', 'professional', 'enterprise'],
    'can_edit_tender': ['free', 'basic', 'professional', 'enterprise'],
    'can_import_tender_data': ['free', 'basic', 'professional', 'enterprise'],

    
    'can_view_boq': ['free', 'basic', 'professional', 'enterprise'],
    'can_create_boq': ['free', 'basic', 'professional', 'enterprise'],
    'can_edit_boq': ['free', 'basic', 'professional', 'enterprise'],
    'can_run_analysis': ['free', 'basic', 'professional', 'enterprise'],
    'can_view_reports': ['free', 'basic', 'professional', 'enterprise'],
    'can_view_competitors': ['free', 'basic', 'professional', 'enterprise'],
    'can_edit_competitors': ['free', 'basic', 'professional', 'enterprise'],
    'can_view_dashboard': ['free', 'basic', 'professional', 'enterprise'],
    'can_view_profile': ['free', 'basic', 'professional', 'enterprise'],
    'can_access_scenario_generator': ['free', 'basic', 'professional', 'enterprise'],
    'can_generate_scenarios': ['free', 'basic', 'professional', 'enterprise'],
    'can_export_scenarios': ['basic', 'professional', 'enterprise'],
}

# =============================================================================
# PAGE ACCESS MAPPING
# =============================================================================

PAGE_ACCESS = {
    # Public pages (no login required)
    'home': {'requires_auth': False},
    'login': {'requires_auth': False},
    'register': {'requires_auth': False},
    'forgot_password': {'requires_auth': False},
    'reset_password': {'requires_auth': False},
    'landing': {'requires_auth': False},
    'contact': {'requires_auth': False},
    
    # Pages that require authentication
    'dashboard': {'requires_auth': True, 'feature': 'can_view_dashboard', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'profile': {'requires_auth': True, 'feature': 'can_view_profile', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    
    # Tender Management
    'tender_management': {'requires_auth': True, 'feature': 'can_view_tenders', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'tender_analysis': {'requires_auth': True, 'feature': 'can_run_analysis', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'new_analysis': {'requires_auth': True, 'feature': 'can_run_analysis', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'analysis_history': {'requires_auth': True, 'feature': 'can_view_reports', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    
    # BOQ Management
    'boq_generator': {'requires_auth': True, 'feature': 'can_create_boq', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'boq_workspace': {'requires_auth': True, 'feature': 'can_create_boq', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    
    # Bid Optimization
    'boq_bid_optimizer': {'requires_auth': True, 'feature': 'can_optimize_bid', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'bid_optimizer': {'requires_auth': True, 'feature': 'can_optimize_bid', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    
    # Competitor Tracking
    'competitor_tracking': {'requires_auth': True, 'feature': 'can_view_competitors', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'competitor_master': {'requires_auth': True, 'feature': 'can_view_competitors', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    
    # Rate Management
    'rate_management': {'requires_auth': True, 'feature': 'can_view_rates', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'rate_editor': {'requires_auth': True, 'feature': 'can_edit_rates', 'roles': ['manager', 'company_admin', 'admin', 'system_admin']},
    'rate_viewer': {'requires_auth': True, 'feature': 'can_view_rates', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'import_wizard': {'requires_auth': True, 'feature': 'can_import_rates', 'roles': ['manager', 'company_admin', 'admin', 'system_admin']},
    
    # User Management
    'user_management': {'requires_auth': True, 'feature': 'can_manage_users', 'roles': ['company_admin', 'admin', 'system_admin']},
    'user_approval': {'requires_auth': True, 'feature': 'can_approve_users', 'roles': ['company_admin', 'admin', 'system_admin']},
    
    # Admin Pages
    'admin_dashboard': {'requires_auth': True, 'feature': 'can_manage_companies', 'roles': ['admin', 'system_admin']},
    'admin_analytics': {'requires_auth': True, 'feature': 'can_view_all_companies', 'roles': ['admin', 'system_admin']},
    'company_analytics': {'requires_auth': True, 'feature': 'can_view_reports', 'roles': ['company_admin', 'manager', 'analyst']},
    'system_config': {'requires_auth': True, 'feature': 'can_manage_system', 'roles': ['system_admin']},
    
    # Extension
    'extension_download': {'requires_auth': True, 'feature': 'can_use_extension', 'roles': ['analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
    'extension_usage': {'requires_auth': True, 'feature': 'can_view_extension_usage', 'roles': ['company_admin', 'admin', 'system_admin']},
    'extension_admin': {'requires_auth': True, 'feature': 'can_manage_system', 'roles': ['system_admin']},
    
    # Subscription
    'subscription': {'requires_auth': True, 'feature': 'can_view_dashboard', 'roles': ['viewer', 'analyst', 'manager', 'company_admin', 'admin', 'system_admin']},
}


class AccessControl:
    """Unified access control system"""
    
    def __init__(self):
        self._subscription_manager = SubscriptionManager(db)
        self._rbac = _rbac
    
    def get_user_role(self) -> str:
        """Get current user's role"""
        return self._rbac.get_current_user_role()
    
    def get_user_plan(self) -> Dict:
        """Get current user's plan info"""
        company_id = st.session_state.get('company_id')
        if company_id:
            return self._subscription_manager.get_company_subscription(company_id)
        return self._subscription_manager._get_default_free_plan()
    
    def check_subscription(self) -> Tuple[bool, str, str]:
        """
        Check current user's subscription access
        
        Returns:
            (has_access: bool, plan: str, message: str)
        """
        company_id = st.session_state.get('company_id')
        user_id = st.session_state.get('user_id')
        return check_subscription_access(
            company_id=company_id,
            user_id=user_id,
            subscription_manager=self._subscription_manager
        )

        

    def has_feature_access(self, feature: str) -> Tuple[bool, str]:
        """
        Check if user has access to a feature (combines RBAC + Plan)
        
        Returns:
            (has_access: bool, reason: str)
        """
        role = self.get_user_role()
        
        # 1. System admins bypass everything
        if role in ['admin', 'system_admin']:
            return True, "System admin access"
        
        # 2. Check RBAC permission
        if not self._rbac.has_permission(feature):
            return False, f"Role '{role}' doesn't have permission: {feature}"
        
        # 3. Check if feature has plan requirements
        plan_requirements = FEATURE_PLAN_REQUIREMENTS.get(feature, [])
        if not plan_requirements:
            return True, "No plan restrictions"
        
        # 4. Check user's plan using subscription check
        has_access, plan, message = self.check_subscription()
        
        # If subscription check failed, deny access
        if not has_access and plan not in ['free']:
            return False, message
        
        # 5. Check if current plan meets requirements
        if plan in plan_requirements:
            return True, f"Access granted via {plan} plan"
        
        # 6. Find the highest required plan
        required = ', '.join([p for p in plan_requirements if p != 'free'])
        return False, f"Requires {required} plan. Current: {plan.upper()}"

    
    def can_access_page(self, page_name: str) -> Tuple[bool, str]:
        """
        Check if user can access a specific page
        
        Returns:
            (has_access: bool, reason: str)
        """
        # Get page config
        page_config = PAGE_ACCESS.get(page_name)
        if not page_config:
            return False, f"Page '{page_name}' not configured"
        
        # Check if page requires authentication
        if page_config.get('requires_auth', True):
            if not st.session_state.get('logged_in', False):
                return False, "Please login to access this page"
        
        # Get required role list
        allowed_roles = page_config.get('roles', [])
        if not allowed_roles:
            return True, "No role restrictions"
        
        # Check if user has one of the required roles
        user_role = self.get_user_role()
        if user_role in allowed_roles:
            return True, f"Role {user_role} has access"
        
        # Check feature-based access
        feature = page_config.get('feature')
        if feature:
            has_feature, reason = self.has_feature_access(feature)
            if has_feature:
                return True, f"Feature access: {feature}"
            return False, reason
        
        return False, f"Role {user_role} not allowed. Required: {', '.join(allowed_roles)}"
    
    def require_access(self, feature: str = None, page: str = None):
        """
        Decorator to require access to a feature or page
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if page:
                    has_access, reason = self.can_access_page(page)
                elif feature:
                    has_access, reason = self.has_feature_access(feature)
                else:
                    has_access, reason = False, "No access check specified"
                
                if not has_access:
                    self.render_access_denied(reason, page or feature)
                    return None
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def render_access_denied(self, reason: str, target: str = None):
        """Render access denied message"""
        st.error(f"🔒 Access Denied: {reason}")
        
        # Suggest actions based on reason
        if "plan" in reason.lower():
            st.info("💡 **Upgrade Required** - This feature requires a higher plan.")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💳 Upgrade Plan", use_container_width=True):
                    st.session_state.page = "subscription"
                    st.rerun()
            with col2:
                if st.button("📋 View Plans", use_container_width=True):
                    st.session_state.page = "subscription"
                    st.rerun()
            with col3:
                if st.button("📞 Contact Support", use_container_width=True):
                    st.session_state.page = "contact"
                    st.rerun()
        elif "permission" in reason.lower() or "role" in reason.lower():
            st.info("👤 **Role Required** - Please contact your administrator to upgrade your role.")
            if st.button("📞 Contact Admin", use_container_width=True):
                st.session_state.page = "contact"
                st.rerun()
        elif "login" in reason.lower():
            if st.button("🔐 Go to Login", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
    
    def get_accessible_pages(self) -> List[str]:
        """Get list of pages accessible to current user"""
        accessible = []
        for page_name, config in PAGE_ACCESS.items():
            has_access, _ = self.can_access_page(page_name)
            if has_access:
                accessible.append(page_name)
        return accessible
    
    def render_navigation_badge(self):
        """Render a badge showing user's role and plan"""
        role = self.get_user_role()
        plan_info = self.get_user_plan()
        plan = plan_info.get('plan', 'free')
        
        role_display = {
            'system_admin': '👑 System Admin',
            'admin': '👑 Admin',
            'company_admin': '🏢 Company Admin',
            'manager': '📊 Manager',
            'analyst': '📈 Analyst',
            'viewer': '👁️ Viewer'
        }.get(role, '👤 User')
        
        plan_display = plan.upper()
        if plan in ['professional', 'enterprise']:
            plan_color = '#10b981'  # Green for premium
        else:
            plan_color = '#6c757d'  # Gray for free
        
        st.sidebar.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 12px; padding: 12px 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: white; font-weight: 600;">{role_display}</span>
                <span style="background: {plan_color}; color: white; 
                          border-radius: 20px; padding: 2px 12px; font-size: 0.75rem; font-weight: 600;">
                    {plan_display}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_menu_items(self):
        """Render sidebar menu items based on access"""
        # Get all accessible pages
        accessible = self.get_accessible_pages()
        
        # Define menu groups
        menu_groups = {
            "📊 Dashboard": ['dashboard', 'company_analytics', 'admin_analytics'],
            "📋 Tenders": ['tender_management', 'tender_analysis', 'analysis_history'],
            "📄 BOQ": ['boq_generator', 'boq_workspace'],
            "🎯 Bid Optimization": ['boq_bid_optimizer', 'bid_optimizer'],
            "👥 Competitors": ['competitor_tracking', 'competitor_master'],
            "📊 Rates": ['rate_management', 'rate_viewer', 'rate_editor', 'import_wizard'],
            "👤 Users": ['user_management', 'user_approval'],
            "⚙️ Admin": ['admin_dashboard', 'system_config', 'extension_admin'],
            "🔧 Settings": ['subscription', 'profile', 'extension_download', 'extension_usage']
        }
        
        # Render menu
        for group_name, pages in menu_groups.items():
            visible_pages = [p for p in pages if p in accessible]
            if visible_pages:
                with st.sidebar.expander(group_name, expanded=True):
                    for page in visible_pages:
                        # Get display name
                        display_name = page.replace('_', ' ').title()
                        if st.button(display_name, key=f"menu_{page}", use_container_width=True):
                            st.session_state.page = page
                            st.rerun()


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

access_control = AccessControl()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def require_page_access(page_name: str):
    """Decorator to require page access"""
    return access_control.require_access(page=page_name)


def require_feature_access(feature: str):
    """Decorator to require feature access"""
    return access_control.require_access(feature=feature)


def has_page_access(page_name: str) -> bool:
    """Check if user has page access"""
    has_access, _ = access_control.can_access_page(page_name)
    return has_access


def has_feature_access(feature: str) -> bool:
    """Check if user has feature access"""
    has_access, _ = access_control.has_feature_access(feature)
    return has_access


def render_access_header():
    """Render access header with role and plan badge"""
    access_control.render_navigation_badge()


def render_sidebar_menu():
    """Render sidebar menu with access control"""
    access_control.render_menu_items()


# =============================================================================
# QUICK ACCESS CHECK FOR PAGES
# =============================================================================

def check_page_access(page_name: str) -> bool:
    """
    Quick function to check page access in page handlers.
    Returns True if accessible, False otherwise.
    """
    has_access, reason = access_control.can_access_page(page_name)
    if not has_access:
        access_control.render_access_denied(reason, page_name)
        return False
    return True