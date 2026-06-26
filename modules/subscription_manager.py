# modules/subscription_manager.py

import streamlit as st
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from modules.subscription import get_plans, get_plan, is_premium_plan

PLANS = get_plans()

from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()

DB_PATH = db.db_path


class SubscriptionManager:
    """Manage company subscriptions and permissions"""
    
    def __init__(self, db):
        self.db = db
    
    # ✅ DELEGATE to crud_operations.py - NO duplicate logic
    def get_company_subscription(self, company_id: int) -> Dict[str, Any]:
        """Get active subscription for a company - delegates to CRUD"""
        return self.db.get_company_subscription(company_id)
    
    def get_user_subscription(self, user_id: int) -> Dict[str, Any]:
        """Get active subscription for a user - delegates to CRUD"""
        return self.db.get_user_subscription(user_id)
    
    def get_plan_config(self, plan_name: str) -> Dict[str, Any]:
        """Get plan configuration from PLANS dict"""
        return PLANS.get(plan_name, PLANS['free'])
    
    def check_extension_limit(self, company_id: int) -> Tuple[bool, int, str]:
        """
        Check if company has reached its extension auto-fill limit.
        
        Returns:
            (can_proceed, remaining, message)
        """
        try:
            # ✅ Use the CRUD method
            sub = self.db.get_company_subscription(company_id)
            plan = sub.get('subscription_tier', 'free')
            
            # Get plan config
            plan_config = PLANS.get(plan, PLANS['free'])
            limit = plan_config.get('extension_auto_fills', 5)
            
            # Get current month usage
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                now = datetime.now()
                start_of_month = datetime(now.year, now.month, 1)
                
                cursor.execute("""
                    SELECT COUNT(*) FROM extension_auto_fill_log
                    WHERE company_id = ? AND filled_at >= ?
                """, (company_id, start_of_month))
                
                row = cursor.fetchone()
                used = row[0] if row else 0
            
            if limit == -1:
                return True, -1, "Unlimited auto-fills"
            
            remaining = max(0, limit - used)
            
            if remaining > 0:
                return True, remaining, f"{remaining} auto-fills remaining this month"
            else:
                return False, 0, f"You've used all {limit} auto-fills this month. Please upgrade your plan."
                
        except Exception as e:
            print(f"Error checking extension limit: {e}")
            return True, -1, "Unable to check limit, proceeding anyway"

    def check_limit(self, company_id: int, resource_type: str) -> Tuple[bool, int, str]:
        """
        Check if company has reached its limit for a resource.
        
        Args:
            company_id: Company ID
            resource_type: 'boq', 'bid_optimization', 'analysis', 'users'
        
        Returns:
            (can_proceed, remaining, message)
        """
        # ✅ Use the CRUD method
        sub = self.db.get_company_subscription(company_id)
        
        resource_map = {
            'boq': ('max_boq_generations', 'boq_used', 'BOQ generations'),
            'bid_optimization': ('max_bid_optimizations', 'bid_optimizations_used', 'bid optimizations'),
            'analysis': ('max_tender_analyses', 'analyses_used', 'tender analyses'),
            'users': ('max_users', None, 'users')
        }
        
        if resource_type not in resource_map:
            return True, -1, "Unknown resource"
        
        max_field, used_field, name = resource_map[resource_type]
        
        # Use subscription_tier from the returned dict
        plan = sub.get('subscription_tier', 'free')
        plan_config = PLANS.get(plan, PLANS['free'])
        
        max_limit = sub.get(max_field, plan_config.get(max_field, 5))
        
        if resource_type == 'users':
            current_used = self._get_company_user_count(company_id)
        else:
            current_used = sub.get(used_field, 0)
        
        if max_limit == -1:
            return True, -1, f"Unlimited {name}"
        
        remaining = max_limit - current_used
        
        if remaining > 0:
            return True, remaining, f"{remaining} {name} remaining"
        else:
            return False, 0, f"No {name} remaining. Please upgrade your plan."
    
    def increment_usage(self, company_id: int, resource_type: str) -> bool:
        """Increment usage counter for a company resource"""
        conn = self.db.get_connection()
        cursor = self.db.db_conn.get_cursor(conn)
        
        field_map = {
            'boq': 'boq_used',
            'bid_optimization': 'bid_optimizations_used',
            'analysis': 'analyses_used'
        }
        
        if resource_type not in field_map:
            return False
        
        field = field_map[resource_type]
        
        try:
            cursor.execute(f"""
                UPDATE subscriptions 
                SET {field} = {field} + 1, updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ? AND status = 'active'
            """, (company_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error incrementing usage: {e}")
            conn.close()
            return False
    
    def _get_company_user_count(self, company_id: int) -> int:
        """Get number of active users in a company"""
        try:
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE company_id = ? AND is_active = 1
                """, (company_id,))
                
                row = cursor.fetchone()
                return row[0] if row else 1
        except:
            return 1
    
    def has_permission(self, company_id: int, permission: str) -> bool:
        """Check if company has a specific permission"""
        # ✅ Use the CRUD method
        sub = self.db.get_company_subscription(company_id)
        
        permission_map = {
            'edit_rates': sub.get('can_edit_rates', False),
            'delete_rates': sub.get('can_delete_rates', False),
            'create_versions': sub.get('can_create_versions', False),
            'export_data': sub.get('can_export_data', False),
            'manage_team': sub.get('can_manage_team', False)
        }
        
        return permission_map.get(permission, False)

        
    # modules/subscription_manager.py - Add this method to the SubscriptionManager class

    def render_usage_stats(self, user_id: int = None) -> None:
        """
        Render usage statistics in sidebar or any UI component.
        
        Args:
            user_id: User ID (defaults to session state)
        """
        import streamlit as st
        
        if user_id is None:
            user_id = st.session_state.get('user_id')
        
        if not user_id:
            return
        
        # Check if user has premium access
        from modules.subscription import is_premium_plan, get_current_user_plan_name
        is_premium = is_premium_plan(get_current_user_plan_name())
        
        if not is_premium:
            return
        
        try:
            # Get user subscription
            sub = self.db.get_user_subscription(user_id)
            limit = sub.get('max_projects', 5)
            used = sub.get('analyses_used', 0)
            
            # Only show if there's a limit
            if limit <= 0:
                return
            
            remaining = max(0, limit - used)
            pct_used = min(100, (used / limit) * 100) if limit > 0 else 0
            
            st.markdown(f"""
            <div style="font-size: 0.8rem; color: #666; text-align: center; margin-top: 0.5rem;">
                <strong>📊 Monthly Usage</strong><br>
                {used}/{limit} analyses used<br>
                <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                    <div style="background: #667eea; width: {pct_used}%; height: 100%; border-radius: 4px;"></div>
                </div>
                <small>{remaining} remaining this month</small>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            # Silently fail - don't break the UI
            pass


    def render_extension_usage_stats(self, company_id: int = None) -> None:
        """
        Render extension usage statistics in sidebar.
        
        Args:
            company_id: Company ID (defaults to session state)
        """
        import streamlit as st
        
        if company_id is None:
            company_id = st.session_state.get('company_id')
        
        if not company_id:
            return
        
        try:
            usage = self.db.get_extension_fill_usage(company_id)
            is_unlimited = usage.get('is_unlimited', False)
            remaining = usage.get('remaining', 0)
            used = usage.get('used', 0)
            limit = usage.get('limit', 5)
            
            if is_unlimited:
                st.markdown("""
                <div style="font-size: 0.8rem; color: #666; text-align: center;">
                    <strong>🤖 Extension</strong><br>
                    <span style="color: #10b981;">Unlimited auto-fills</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="font-size: 0.8rem; color: #666; text-align: center;">
                    <strong>🤖 Extension Auto-Fills</strong><br>
                    {remaining} remaining this month<br>
                    <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                        <div style="background: #667eea; width: {min(100, (used / limit) * 100) if limit > 0 else 0}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <small>{used} used this month</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
        except Exception as e:
            # Silently fail
            pass
def check_subscription_and_permission(db, resource_type=None, permission=None):
    """
    Check subscription limits and permissions.
    
    Args:
        db: Database instance
        resource_type: 'boq', 'bid_optimization', 'analysis', 'users'
        permission: 'edit_rates', 'delete_rates', 'create_versions', 'export_data', 'manage_team'
    
    Returns:
        (can_proceed, message)
    """
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    
    # Admins bypass limits
    if user_role in ['admin', 'system_admin']:
        return True, "OK"
    
    if not company_id:
        return False, "No company associated with this account"
    
    sub_manager = SubscriptionManager(db)
    
    if resource_type:
        can_proceed, remaining, message = sub_manager.check_limit(company_id, resource_type)
        if not can_proceed:
            return False, message
    
    if permission:
        has_perm = sub_manager.has_permission(company_id, permission)
        if not has_perm:
            return False, f"You don't have permission to {permission.replace('_', ' ')}. Please upgrade your plan."
    
    return True, "OK"

# =============================================================================
# SUBSCRIPTION ACCESS CHECK
# =============================================================================

def check_subscription_access(company_id: int = None, user_id: int = None, subscription_manager: Optional['SubscriptionManager'] = None) -> Tuple[bool, str, str]:
    """
    Check subscription access - uses correct logic based on user type
    
    Args:
        company_id: Company ID (optional)
        user_id: User ID (optional, defaults to current user)
        subscription_manager: Optional SubscriptionManager instance
    
    Returns:
        (has_access: bool, plan: str, message: str)
    """
    print("=" * 60)
    print("🔍 check_subscription_access() called")
    print("=" * 60)
    
    # Get user info
    from modules.rbac import get_current_user_role
    user_role = get_current_user_role()
    print(f"   👤 User role: {user_role}")
    
    # System admin bypass - full access
    if user_role in ['system_admin', 'admin']:
        print("   ✅ System admin - Full access granted")
        return True, 'system_admin', "System Admin - Full access"
    
    # Get user_id if not provided
    if user_id is None:
        user_id = st.session_state.get('user_id')
    
    if not user_id:
        print("   ❌ No user ID found")
        return False, 'free', "User not found"
    
    # ✅ Get the effective plan using the new logic
    from modules.subscription import get_effective_plan_for_user
    effective = get_effective_plan_for_user(user_id)
    
    plan = effective.get('plan', 'free')
    source = effective.get('source', 'none')
    
    print(f"   📊 Effective Plan: {plan} (Source: {source})")
    
    if plan != 'free':
        print(f"   ✅ Access granted - {plan.upper()} plan ({source})")
        return True, plan, f"{source.upper()} subscription - {plan.upper()} plan"
    
    print(f"   ❌ No active subscription found")
    return False, 'free', "No active subscription found. Please subscribe."



def check_premium_access(company_id: int) -> bool:
    """
    Quick check if company has premium access (Professional or Enterprise)
    
    Args:
        company_id: Company ID
    
    Returns:
        bool: True if premium access, False otherwise
    """
    has_access, _, _ = check_subscription_access(company_id)
    return has_access



def render_subscription_badge(self, user_id: int = None) -> None:
    """
    Render a small subscription badge for the sidebar.
    
    Args:
        user_id: User ID (defaults to session state)
    """
    import streamlit as st
    
    if user_id is None:
        user_id = st.session_state.get('user_id')
    
    if not user_id:
        return
    
    from modules.subscription import get_plan, get_current_user_plan_name
    
    plan_name = get_current_user_plan_name()
    plan_config = get_plan(plan_name)
    
    if not plan_config:
        return
    
    is_premium = plan_name in ['professional', 'enterprise']
    badge_color = plan_config.get('color', '#6c757d')
    badge_icon = plan_config.get('badge', '📋')
    display_name = plan_config.get('name', plan_name.title())
    
    st.markdown(f"""
    <div style="text-align: center; background: {badge_color}15; 
                padding: 0.4rem; border-radius: 6px; margin: 0.5rem 0; 
                border: 1px solid {badge_color}30;">
        <span style="color: {badge_color}; font-weight: 600; font-size: 0.85rem;">
            {badge_icon} {display_name}
        </span>
        <span style="font-size: 0.7rem; color: {badge_color}; opacity: 0.7; margin-left: 4px;">
            {'✨ PREMIUM' if is_premium else '🆓 FREE'}
        </span>
    </div>
    """, unsafe_allow_html=True)