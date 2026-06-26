"""
Authentication Module for TenderAI
Handles user authentication, login, logout, and permission checks
"""

import streamlit as st
from database.unified_db_manager import UnifiedDatabaseManager
import time
import hashlib
import json
import traceback
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)
db = UnifiedDatabaseManager()


def save_session_to_url(remember_me=False):
    """Save session to URL parameters for persistence"""
    if not remember_me:
        return
    
    if st.session_state.get('logged_in', False):
        # ✅ Save to URL parameters
        st.query_params['user_id'] = str(st.session_state.user_id)
        st.query_params['username'] = st.session_state.username
        st.query_params['expiry'] = str(int(time.time()) + 30 * 24 * 3600)
        print(f"✅ Session saved to URL for user: {st.session_state.username}")
        print(f"   Params: {dict(st.query_params)}")  # Debug


# modules/auth.py - Update restore_session_from_url

def restore_session_from_url():
    """Restore session from URL parameters"""
    print("=" * 50)
    print("RESTORE_SESSION_FROM_URL CALLED")
    
    # Already logged in
    if st.session_state.get('logged_in', False):
        print("User already logged in, skipping restore")
        return True
    
    # Check URL parameters
    params = st.query_params
    print(f"URL params: {dict(params)}")
    
    if 'user_id' in params and 'username' in params and 'expiry' in params:
        try:
            # Check expiry
            current_time = int(time.time())
            expiry_time = int(params['expiry'])
            
            if expiry_time <= current_time:
                print("Session expired")
                st.query_params.clear()
                return False
            
            user_id = int(params['user_id'])
            username = params['username']
            print(f"Looking up user: id={user_id}")
            
            # Get user from database
            user = db.get_user_by_id(user_id)
            
            if not user:
                print("User not found")
                st.query_params.clear()
                return False
            
            # Verify username matches
            if user.get('username') != username:
                print(f"Username mismatch: DB='{user.get('username')}', URL='{username}'")
                st.query_params.clear()
                return False
            
            print(f"✅ User verified: {user.get('username')}")
            
            # Restore session from dictionary
            st.session_state.logged_in = True
            st.session_state.user_id = user.get('id')
            st.session_state.username = user.get('username')
            st.session_state.user_email = user.get('email')
            st.session_state.user_mobile = user.get('mobile_number')
            st.session_state.full_name = user.get('full_name') or user.get('username')
            st.session_state.user_role = user.get('role', 'user')
            st.session_state.company_id = user.get('company_id')
            st.session_state.mobile_verified = user.get('mobile_verified', False)
            st.session_state.email_verified = user.get('email_verified', False)
            st.session_state.remember_me = True
            
            # Get company name
            if st.session_state.company_id:
                company = db.get_company_by_id(st.session_state.company_id)
                st.session_state.company_name = company.get('company_name', 'N/A') if company else 'N/A'
            else:
                st.session_state.company_name = "Individual"
            
            # Set subscription plan
            if st.session_state.user_role in ['admin', 'system_admin']:
                st.session_state.subscription_plan = 'professional'
            else:
                st.session_state.subscription_plan = 'free'
            st.session_state.subscription_status = 'active'
            
            print(f"✅ Session restored for user: {st.session_state.username}")
            print(f"✅ Role: {st.session_state.user_role}")
            print(f"✅ Company: {st.session_state.company_name}")
            
            # ✅ CRITICAL: Clear URL params after restore
            st.query_params.clear()
            print("✅ URL params cleared")
            
            return True
            
        except Exception as e:
            print(f"Restore error: {e}")
            import traceback
            traceback.print_exc()
            st.query_params.clear()
    
    print("❌ No valid session params found in URL")
    return False


def clear_session_url():
    """Clear session from URL"""
    st.query_params.clear()

# modules/auth.py

def login_user(user_data: Dict, password: str = None, remember_me: bool = False) -> bool:
    """Login user and set session state"""
    if not user_data:
        return False
    
    try:
        st.session_state.logged_in = True
        st.session_state.user_id = user_data.get('id')
        st.session_state.username = user_data.get('username')
        st.session_state.user_email = user_data.get('email')
        st.session_state.user_mobile = user_data.get('mobile_number')
        st.session_state.full_name = user_data.get('full_name') or user_data.get('username')
        st.session_state.user_role = user_data.get('role', 'user')
        st.session_state.company_id = user_data.get('company_id')
        st.session_state.mobile_verified = user_data.get('mobile_verified', False)
        st.session_state.email_verified = user_data.get('email_verified', False)
        st.session_state.account_type = 'company' if user_data.get('company_id') else 'individual'
        
        print(f"✅ Login - Role set to: {st.session_state.user_role}")
        print(f"✅ Login - Company ID: {st.session_state.company_id}")

        # Fetch company name
        if st.session_state.company_id:
            company = db.get_company_by_id(st.session_state.company_id)
            st.session_state.company_name = company.get('company_name', 'N/A') if company else 'N/A'
        else:
            st.session_state.company_name = "Individual"
        
        # Set subscription plan
        if st.session_state.user_role in ['admin', 'system_admin']:
            st.session_state.subscription_plan = 'professional'
        else:
            st.session_state.subscription_plan = 'free'
        st.session_state.subscription_status = 'active'
        
        # ✅ Refresh RBAC role cache
        from modules.rbac import _rbac
        _rbac.refresh_role()
        
        # ✅ Save to URL if remember_me is checked
        if remember_me:
            save_session_to_url(remember_me)
        
        logger.info(f"User {st.session_state.username} logged in successfully")
        return True
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        traceback.print_exc()
        return False


def logout_user():
    """Logout current user and clear URL params"""
    clear_session_url()
    
    keys_to_clear = [
        'logged_in', 'user_id', 'username', 'user_email', 'user_mobile',
        'full_name', 'user_role', 'company_id', 'company_name',
        'subscription_plan', 'subscription_status', 'mobile_verified',
        'email_verified', 'account_type', 'remember_me'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Also clear any pending states
    if 'show_2fa' in st.session_state:
        del st.session_state.show_2fa
    if 'pending_2fa' in st.session_state:
        del st.session_state.pending_2fa
    if 'verification_step' in st.session_state:
        del st.session_state.verification_step
    if 'pending_registration' in st.session_state:
        del st.session_state.pending_registration
    
    st.session_state.logged_in = False
    st.session_state.page = 'home'
    logger.info("User logged out")
    return True


def authenticate_user(username_or_email: str, password: str) -> Optional[Dict]:
    """
    Authenticate user by username or email
    Returns user DICTIONARY or None
    """
    return db.authenticate_user(username_or_email, password)


def authenticate_individual_user(email: str, password: str) -> Optional[Dict]:
    """
    Authenticate individual user (same as authenticate_user)
    """
    return db.authenticate_user(email, password)


def is_admin() -> bool:
    """Check if current user is admin"""
    role = st.session_state.get('user_role', '')
    return role in ['admin', 'system_admin']


def is_company_admin() -> bool:
    """Check if current user is company admin"""
    role = st.session_state.get('user_role', '')
    return role in ['admin', 'system_admin', 'company_admin']


def has_permission(required_role: str) -> bool:
    """Check if user has required role permission"""
    role_hierarchy = {
        'system_admin': 5,
        'admin': 5,
        'company_admin': 4,
        'manager': 3,
        'analyst': 2,
        'viewer': 1,
        'individual': 1
    }
    current_role = st.session_state.get('user_role', 'viewer')
    return role_hierarchy.get(current_role, 0) >= role_hierarchy.get(required_role, 0)


def get_current_user() -> Optional[Dict]:
    """Get current user details"""
    if st.session_state.get('logged_in'):
        return {
            'id': st.session_state.get('user_id'),
            'username': st.session_state.get('username'),
            'email': st.session_state.get('user_email'),
            'mobile': st.session_state.get('user_mobile'),
            'full_name': st.session_state.get('full_name'),
            'role': st.session_state.get('user_role'),
            'company_id': st.session_state.get('company_id'),
            'company_name': st.session_state.get('company_name'),
            'mobile_verified': st.session_state.get('mobile_verified', False),
            'email_verified': st.session_state.get('email_verified', False)
        }
    return None


def is_user_approved(user_id: int = None) -> bool:
    """Check if user is approved"""
    if user_id is None:
        user_id = st.session_state.get('user_id')
    if user_id:
        # Get user from DB
        user = db.get_user_by_id(user_id)
        return user.get('is_active', False) if user else False
    return False


def get_refresh_warning():
    """Display warning about browser refresh behavior"""
    if st.session_state.get('logged_in', False):
        st.sidebar.info(
            "🔄 **Tip:** Browser refresh won't log you out if 'Remember Me' was checked.\n\n"
            "Use the Logout button below to end your session."
        )


def require_auth(redirect_page: str = "login"):
    """Decorator-like function to require authentication"""
    if not st.session_state.get('logged_in', False):
        st.warning("Please login to access this page")
        navigate_to(redirect_page)
        st.rerun()
        return False
    return True


def require_role(required_role: str, redirect_page: str = "dashboard"):
    """Check if user has required role"""
    if not has_permission(required_role):
        st.error(f"Access denied. {required_role.title()} privileges required.")
        navigate_to(redirect_page)
        st.rerun()
        return False
    return True


def navigate_to(page: str, success_msg: str = None):
    """Navigate to a page"""
    if success_msg:
        st.success(success_msg)
    st.session_state.page = page

def is_oauth_callback() -> bool:
    """Check if current request is an OAuth callback"""
    return 'code' in st.query_params
