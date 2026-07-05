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
import secrets
import bcrypt
from typing import Optional, Dict, List, Any, Tuple
from utils.otp_service import OTPService

logger = logging.getLogger(__name__)
db = UnifiedDatabaseManager()

def save_session_to_url(remember_me: bool = False):
    """Save session to URL for persistence"""
    try:
        if remember_me:
            import hashlib
            import time
            
            user_id = st.session_state.get('user_id')
            username = st.session_state.get('username')
            expiry = int(time.time()) + (30 * 24 * 60 * 60)  # 30 days
            
            token = f"{user_id}:{username}:{expiry}"
            
            st.query_params.user_id = str(user_id)
            st.query_params.username = username
            st.query_params.expiry = str(expiry)
            st.query_params.token = hashlib.sha256(token.encode()).hexdigest()[:16]
            
            print(f"✅ Session saved for user: {username}")
    except Exception as e:
        print(f"⚠️ Could not save session: {e}")



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
            st.session_state.two_factor_verified = True  # Session already verified

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
    """Login user - with global 2FA"""
    if not user_data:
        return False
    
    try:
        user_id = user_data.get('id')
        email = user_data.get('email')
         # ✅ Check if already logged in
        if st.session_state.get('logged_in', False) and st.session_state.get('user_id') == user_id:
            print(f"✅ User {user_id} already logged in")
            return True
        
        # ✅ Check if 2FA already verified
        if st.session_state.get('two_factor_verified', False):
            print(f"✅ 2FA already verified for user {user_id}")
            return _complete_login(user_data, remember_me)
        
        # ✅ Check if we're in 2FA flow
        if st.session_state.get('verification_step') == '2fa_otp':
            print(f"⏳ 2FA flow in progress for user {user_id}")
            return True
        
        
        # ✅ Store pending login info and send OTP
        st.session_state.pending_2fa_user_id = user_id
        st.session_state.pending_2fa_user_data = user_data
        st.session_state.pending_2fa_remember_me = remember_me
        st.session_state.verification_step = '2fa_otp'
        
        # Send OTP
        otp_service = OTPService(db)
        success, message, otp_code = otp_service.send_verification_otp(
            contact_type='email',
            contact_value=email,
            target_type='user',
            target_id=user_id,
            purpose='2fa_login'
        )
        
        if success:
            st.session_state._2fa_otp_sent = True
            st.session_state._2fa_otp_code = otp_code
            st.session_state._2fa_contact = email
            print(f"✅ 2FA OTP sent to: {email}")
            return True  # Will show 2FA verification screen
        else:
            st.error(f"Failed to send verification code: {message}")
            return False
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        traceback.print_exc()
        return False

def verify_2fa_otp(otp_code: str) -> Tuple[bool, str]:
    """
    Verify 2FA OTP and complete login
    """
    try:
        user_id = st.session_state.get('pending_2fa_user_id')
        if not user_id:
            return False, "Session expired. Please login again."
        
        user_data = st.session_state.get('pending_2fa_user_data', {})
        email = user_data.get('email')
        
        otp_service = OTPService(db)
        success, message, _ = otp_service.verify_otp(
            contact_type='email',
            contact_value=email,
            otp_code=otp_code,
            purpose='2fa_login'
        )
        
        if success:
            # Mark 2FA as verified in session
            st.session_state.two_factor_verified = True
            
            # Mark in database
            db.execute("""
                UPDATE users 
                SET two_factor_verified = TRUE,
                    two_factor_verified_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            
            # Complete login
            remember_me = st.session_state.get('pending_2fa_remember_me', False)
            _complete_login(user_data, remember_me)
            
            # Clear pending state
            _clear_pending_2fa_state()
            
            return True, "Verification successful!"
        else:
            return False, message
            
    except Exception as e:
        logger.error(f"2FA verification error: {e}")
        traceback.print_exc()
        return False, f"Verification failed: {str(e)}"

def _complete_login(user_data: Dict, remember_me: bool = False) -> bool:
    """Complete the login process"""
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
        st.session_state.two_factor_verified = True
        
        print(f"✅ Login - Role: {st.session_state.user_role}")
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
        
        # Refresh RBAC
        from modules.rbac import _rbac
        _rbac.refresh_role()
        
        # Save to URL if remember_me
        if remember_me:
            save_session_to_url(remember_me)
        
        logger.info(f"User {st.session_state.username} logged in successfully")
        return True
        
    except Exception as e:
        logger.error(f"Login completion error: {e}")
        traceback.print_exc()
        return False


def _clear_pending_2fa_state():
    """Clear pending 2FA session state"""
    keys_to_clear = [
        'pending_2fa_user_id',
        'pending_2fa_user_data',
        'pending_2fa_remember_me',
        '_2fa_otp_sent',
        '_2fa_otp_code',
        '_2fa_contact'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.verification_step = None


def resend_2fa_otp() -> Tuple[bool, str]:
    """Resend 2FA OTP"""
    try:
        user_id = st.session_state.get('pending_2fa_user_id')
        if not user_id:
            return False, "Session expired. Please login again."
        
        user_data = st.session_state.get('pending_2fa_user_data', {})
        email = user_data.get('email')
        
        otp_service = OTPService(db)
        success, message, otp_code = otp_service.resend_otp(
            contact_type='email',
            contact_value=email,
            target_type='user',
            target_id=user_id,
            purpose='2fa_login'
        )
        
        if success:
            st.session_state._2fa_otp_code = otp_code
            return True, "New verification code sent!"
        else:
            return False, message
            
    except Exception as e:
        logger.error(f"Resend 2FA OTP error: {e}")
        return False, str(e)

# modules/auth.py - Add this function

def logout_user():
    """Log out the current user and clear OIDC session"""
    print("=" * 60)
    print("🚪 LOGGING OUT USER")
    print("=" * 60)
    
    try:
        # Clear app session state
        keys_to_clear = ['logged_in', 'user_id', 'user_role', 'user_name', 'user_email', 'page']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Clear any OIDC-related session state
        oidc_keys = ['google_user_info', 'show_google_registration', 'google_registration_mode']
        for key in oidc_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # IMPORTANT: Clear Streamlit's OIDC session
        # This is the key to actually logging out from Google
        if hasattr(st, 'user'):
            # Try to logout using Streamlit's OIDC
            try:
                # Some versions of Streamlit support this
                if hasattr(st, 'logout'):
                    st.logout()
                    print("✅ Called st.logout()")
            except Exception as e:
                print(f"⚠️ st.logout() not available: {e}")
            
            # Clear the user object reference
            # st.user is read-only, but we can clear the session
            try:
                # Force clear by redirecting to a logout URL
                # This works by clearing the OIDC session cookie
                import urllib.parse
                redirect_uri = get_redirect_uri()
                # Redirect to Google logout endpoint
                logout_url = "https://accounts.google.com/logout"
                st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
                print("✅ Redirecting to Google logout...")
            except Exception as e:
                print(f"⚠️ Could not redirect to Google logout: {e}")
        
        # Clear query params
        st.query_params.clear()
        
        # Set page to login
        st.session_state.page = "login"
        
        print("✅ User logged out successfully")
        print("=" * 60)
        
        return True
    except Exception as e:
        print(f"❌ Logout error: {e}")
        import traceback
        traceback.print_exc()
        return False


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

def create_user_from_google(user_info):
    """Create a new user from Google OAuth data"""
    
    print(f"🔍 DEBUG: create_user_from_google called with {user_info.get('email')}")
    
    try:
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        google_id = user_info.get('id')
        picture = user_info.get('picture', '')
        
        # Generate a random username from email
        username = email.split('@')[0]
        # Make sure username is unique
        counter = 1
        original_username = username
        while True:
            existing_user = db.query_one("SELECT id FROM users WHERE username = ?", (username,))
            if not existing_user:
                break
            username = f"{original_username}{counter}"
            counter += 1
        
        # Create user data
        user_data = {
            'username': username,
            'email': email,
            'full_name': name,
            'phone': '',
            'mobile_number': '',  # Empty for Google users
            'google_id': google_id,
            'picture': picture,
        }
        
        print(f"🔍 DEBUG: Creating Google user with data: {user_data}")
        
        # Use the new create_google_user method with OAuth support
        success, user_id = db.create_google_user(user_data)
        
        if success:
            print(f"✅ Google user created with ID: {user_id}")
            return user_id
        else:
            print(f"❌ Failed to create Google user: {user_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating Google user: {e}")
        import traceback
        traceback.print_exc()
        return None