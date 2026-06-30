# modules/google_auth.py - Using Streamlit's built-in OIDC

import streamlit as st
import os
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager
import logging

logger = logging.getLogger(__name__)
db = UnifiedDatabaseManager()

# modules/google_auth.py - Fixed credential checking

import streamlit as st
import os
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager
import logging

logger = logging.getLogger(__name__)
db = UnifiedDatabaseManager()


def is_oidc_configured():
    """Check if OIDC is properly configured in secrets"""
    try:
        # Check for [auth] section
        if "auth" in st.secrets:
            auth_config = st.secrets["auth"]
            required_fields = ["client_id", "client_secret", "cookie_secret", "redirect_uri"]
            if all(field in auth_config for field in required_fields):
                print("✅ OIDC configured in [auth] section")
                return True
        
        # Check for flat structure
        required_fields = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
        if all(field in st.secrets for field in required_fields):
            print("✅ OIDC configured with flat structure")
            return True
            
        # Check environment variables
        if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
            print("✅ OIDC configured with environment variables")
            return True
            
        print("❌ OIDC not configured")
        return False
    except Exception as e:
        print(f"❌ Error checking OIDC config: {e}")
        return False


def handle_google_callback():
    """Handle Google OAuth callback using Streamlit's built-in OIDC"""
    
    # Check if user is authenticated via Streamlit's OIDC
    try:
        if hasattr(st, 'user') and st.user:
            # Get user info from st.user
            email = st.user.get('email')
            name = st.user.get('name', email.split('@')[0] if email else '')
            
            if not email:
                return None
            
            print(f"✅ Google authentication successful: {email}")
            
            # Check if this is a registration flow or login flow
            is_registration_mode = st.session_state.get('google_registration_mode', False)
            
            # Check if user exists
            existing_user = db.get_user_by_email(email)
            
            if existing_user and not is_registration_mode:
                # Login flow - user exists
                from modules.auth import login_user
                login_user(existing_user, None, remember_me=True)
                st.success(f"Welcome back, {existing_user.get('full_name', name)}! 🎉")
                
                from modules.auth import save_session_to_url
                save_session_to_url(True)
                
                # Clear registration mode
                st.session_state.google_registration_mode = False
                
                return {'logged_in': True, 'user_id': existing_user['id']}
            
            elif existing_user and is_registration_mode:
                # Registration flow but user already exists
                print("🔍 User exists but trying to register")
                st.warning(f"An account with {email} already exists. Please login instead.")
                st.session_state.google_registration_mode = False
                
                # Redirect to login
                st.session_state.page = 'login'
                st.rerun()
                return None
            
            else:
                # New user - either registration or auto-login
                if is_registration_mode:
                    # Registration flow - store data for registration
                    print("🔍 Registration flow - storing Google data")
                    st.session_state.pending_google_signup = {
                        'email': email,
                        'name': name,
                        'google_id': st.user.get('sub'),
                        'picture': st.user.get('picture', '')
                    }
                    st.session_state.show_google_registration = True
                    st.session_state.google_registration_mode = False
                    return {'show_registration': True, 'user_data': st.session_state.pending_google_signup}
                else:
                    # Login flow - auto-register new user
                    print("🔍 Auto-registering new user from login")
                    
                    try:
                        from modules.auth import create_user_from_google
                        google_user_info = {
                            'id': st.user.get('sub'),
                            'email': email,
                            'name': name,
                            'picture': st.user.get('picture', '')
                        }
                        user_id = create_user_from_google(google_user_info)
                        
                        if user_id:
                            # Login the new user
                            user_data = db.get_user_by_id(user_id)
                            if user_data:
                                from modules.auth import login_user
                                login_user(user_data, None, remember_me=True)
                                st.success(f"Welcome, {name}! Your account has been created. 🎉")
                                
                                from modules.auth import save_session_to_url
                                save_session_to_url(True)
                                
                                # Clear registration mode
                                st.session_state.google_registration_mode = False
                                
                                return {'logged_in': True, 'user_id': user_id}
                        else:
                            st.error("❌ Failed to create account. Please try again.")
                            return None
                            
                    except Exception as e:
                        print(f"❌ Auto-registration error: {e}")
                        import traceback
                        traceback.print_exc()
                        st.error(f"Failed to create account: {str(e)}")
                        return None
                        
    except Exception as e:
        print(f"❌ OIDC user info error: {e}")
        return None
    
    return None


def render_google_login_button(registration_mode=False):
    """Render Google Sign-In button using Streamlit's built-in OIDC"""
    
    # Check if OIDC is configured
    if not is_oidc_configured():
        st.warning("⚠️ Google Sign-In is not configured. Please contact administrator.")
        # Print debug info
        print("🔍 Debug: st.secrets keys:", list(st.secrets.keys()) if hasattr(st, 'secrets') else "No secrets")
        if hasattr(st, 'secrets') and "auth" in st.secrets:
            print("🔍 Debug: auth keys:", list(st.secrets["auth"].keys()))
        return
    
    # Store registration mode
    if registration_mode:
        st.session_state.google_registration_mode = True
    
    button_text = "Sign up with Google" if registration_mode else "Sign in with Google"
    
    # Use Streamlit's built-in login button
    if st.button(button_text, type="primary", use_container_width=True, key=f"google_{'register' if registration_mode else 'login'}"):
        # Trigger OIDC flow
        st.login()


def render_google_registration_form(db_instance):
    """Render registration completion form for Google users"""
    
    user_info = st.session_state.get('pending_google_signup', {})
    
    if not user_info:
        st.error("Session expired. Please try again.")
        st.session_state.show_google_registration = False
        return
    
    st.markdown("### ✅ Complete Your Registration with Google")
    st.info(f"👋 Welcome **{user_info.get('name', '')}**! Please complete your registration.")
    
    with st.form("google_registration_form"):
        # Pre-filled fields from Google
        st.text_input("Email", value=user_info.get('email', ''), disabled=True)
        full_name = st.text_input("Full Name *", value=user_info.get('name', ''))
        username = st.text_input("Username *", value=user_info.get('email', '').split('@')[0])
        
        st.markdown("---")
        st.markdown("#### Additional Information (Optional)")
        
        mobile = st.text_input("Mobile Number (Optional)", placeholder="01XXXXXXXXX - You can add this later")
        phone = st.text_input("Phone (Alternative)", placeholder="Your phone number")
        
        st.caption("💡 You can add your mobile number later from your profile settings.")
        
        specialization = st.selectbox(
            "Specialization",
            ["", "Construction Consultant", "Bid Analyst", "Quantity Surveyor", 
            "Project Manager", "Civil Engineer", "Architect", "Other"]
        )
        years_experience = st.slider("Years of Experience", 0, 40, 5)
        
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *")
        
        submitted = st.form_submit_button("✅ Complete Registration with Google", type="primary", use_container_width=True)
        
        if submitted:
            errors = []
            if not full_name:
                errors.append("Full name is required")
            if not username:
                errors.append("Username is required")
            if not terms:
                errors.append("You must agree to the Terms of Service")
            
            # Validate mobile only if provided
            if mobile:
                from utils.validators import normalize_mobile, validate_bangladesh_mobile
                normalized_mobile = normalize_mobile(mobile)
                if not validate_bangladesh_mobile(normalized_mobile):
                    errors.append("Invalid Bangladeshi mobile number")
                else:
                    mobile = normalized_mobile
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # Store pending registration
                st.session_state.pending_registration = {
                    'account_type': 'individual',
                    'full_name': full_name.strip(),
                    'username': username.strip(),
                    'email': user_info['email'],
                    'mobile': mobile if mobile else '',
                    'phone': phone,
                    'specialization': specialization,
                    'years_experience': years_experience,
                    'is_google_user': True,
                    'google_id': user_info.get('google_id'),
                    'password': None  # No password needed for Google users
                }
                
                # Skip OTP for Google users since they're already verified by Google
                st.session_state.verification_step = 'email_otp'
                st.session_state.verification_contact = user_info['email']
                st.session_state.verification_purpose = 'google_registration'
                st.session_state.temp_otp_code = 'GOOGLE_VERIFIED'
                
                st.success("✅ Google account verified! Completing registration...")
                complete_registration()
                st.rerun()


def complete_registration():
    """Complete the registration process for Google users"""
    from modules.auth import complete_registration as auth_complete_registration
    return auth_complete_registration()


def get_oidc_component():
    """Legacy function - returns None as we're using built-in OIDC"""
    return None
def handle_google_callback():
    """Handle Google OAuth callback using Streamlit's built-in OIDC"""
    
    # Check if user is authenticated via Streamlit's OIDC
    try:
        if hasattr(st, 'user') and st.user:
            # Get user info from st.user
            email = st.user.get('email')
            name = st.user.get('name', email.split('@')[0] if email else '')
            
            if not email:
                return None
            
            print(f"✅ Google authentication successful: {email}")
            
            # Check if this is a registration flow or login flow
            is_registration_mode = st.session_state.get('google_registration_mode', False)
            
            # Check if user exists
            existing_user = db.get_user_by_email(email)
            
            if existing_user and not is_registration_mode:
                # Login flow - user exists
                from modules.auth import login_user
                login_user(existing_user, None, remember_me=True)
                st.success(f"Welcome back, {existing_user.get('full_name', name)}! 🎉")
                
                from modules.auth import save_session_to_url
                save_session_to_url(True)
                
                # Clear registration mode
                st.session_state.google_registration_mode = False
                
                return {'logged_in': True, 'user_id': existing_user['id']}
            
            elif existing_user and is_registration_mode:
                # Registration flow but user already exists
                print("🔍 User exists but trying to register")
                st.warning(f"An account with {email} already exists. Please login instead.")
                st.session_state.google_registration_mode = False
                
                # Redirect to login
                st.session_state.page = 'login'
                st.rerun()
                return None
            
            else:
                # New user - either registration or auto-login
                if is_registration_mode:
                    # Registration flow - store data for registration
                    print("🔍 Registration flow - storing Google data")
                    st.session_state.pending_google_signup = {
                        'email': email,
                        'name': name,
                        'google_id': st.user.get('sub'),
                        'picture': st.user.get('picture', '')
                    }
                    st.session_state.show_google_registration = True
                    st.session_state.google_registration_mode = False
                    return {'show_registration': True, 'user_data': st.session_state.pending_google_signup}
                else:
                    # Login flow - auto-register new user
                    print("🔍 Auto-registering new user from login")
                    
                    try:
                        from modules.auth import create_user_from_google
                        google_user_info = {
                            'id': st.user.get('sub'),
                            'email': email,
                            'name': name,
                            'picture': st.user.get('picture', '')
                        }
                        user_id = create_user_from_google(google_user_info)
                        
                        if user_id:
                            # Login the new user
                            user_data = db.get_user_by_id(user_id)
                            if user_data:
                                from modules.auth import login_user
                                login_user(user_data, None, remember_me=True)
                                st.success(f"Welcome, {name}! Your account has been created. 🎉")
                                
                                from modules.auth import save_session_to_url
                                save_session_to_url(True)
                                
                                # Clear registration mode
                                st.session_state.google_registration_mode = False
                                
                                return {'logged_in': True, 'user_id': user_id}
                        else:
                            st.error("❌ Failed to create account. Please try again.")
                            return None
                            
                    except Exception as e:
                        print(f"❌ Auto-registration error: {e}")
                        import traceback
                        traceback.print_exc()
                        st.error(f"Failed to create account: {str(e)}")
                        return None
                        
    except Exception as e:
        print(f"❌ OIDC user info error: {e}")
        return None
    
    return None

def render_google_login_button(registration_mode=False):
    """Render Google Sign-In button using Streamlit's built-in OIDC"""
    
    # Check if OIDC is configured
    if not is_oidc_configured():
        st.warning("⚠️ Google Sign-In is not configured. Please contact administrator.")
        # Print debug info
        print("🔍 Debug: st.secrets keys:", list(st.secrets.keys()) if hasattr(st, 'secrets') else "No secrets")
        if hasattr(st, 'secrets') and "auth" in st.secrets:
            print("🔍 Debug: auth keys:", list(st.secrets["auth"].keys()))
        return
    
    # Store registration mode
    if registration_mode:
        st.session_state.google_registration_mode = True
    
    button_text = "Sign up with Google" if registration_mode else "Sign in with Google"
    
    # Use Streamlit's built-in login button
    if st.button(button_text, type="primary", use_container_width=True, key=f"google_{'register' if registration_mode else 'login'}"):
        # Trigger OIDC flow
        st.login()

def render_google_registration_form(db_instance):
    """Render registration completion form for Google users"""
    
    user_info = st.session_state.get('pending_google_signup', {})
    
    if not user_info:
        st.error("Session expired. Please try again.")
        st.session_state.show_google_registration = False
        return
    
    st.markdown("### ✅ Complete Your Registration with Google")
    st.info(f"👋 Welcome **{user_info.get('name', '')}**! Please complete your registration.")
    
    with st.form("google_registration_form"):
        # Pre-filled fields from Google
        st.text_input("Email", value=user_info.get('email', ''), disabled=True)
        full_name = st.text_input("Full Name *", value=user_info.get('name', ''))
        username = st.text_input("Username *", value=user_info.get('email', '').split('@')[0])
        
        st.markdown("---")
        st.markdown("#### Additional Information (Optional)")
        
        mobile = st.text_input("Mobile Number (Optional)", placeholder="01XXXXXXXXX - You can add this later")
        phone = st.text_input("Phone (Alternative)", placeholder="Your phone number")
        
        st.caption("💡 You can add your mobile number later from your profile settings.")
        
        specialization = st.selectbox(
            "Specialization",
            ["", "Construction Consultant", "Bid Analyst", "Quantity Surveyor", 
            "Project Manager", "Civil Engineer", "Architect", "Other"]
        )
        years_experience = st.slider("Years of Experience", 0, 40, 5)
        
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *")
        
        submitted = st.form_submit_button("✅ Complete Registration with Google", type="primary", use_container_width=True)
        
        if submitted:
            errors = []
            if not full_name:
                errors.append("Full name is required")
            if not username:
                errors.append("Username is required")
            if not terms:
                errors.append("You must agree to the Terms of Service")
            
            # Validate mobile only if provided
            if mobile:
                from utils.validators import normalize_mobile, validate_bangladesh_mobile
                normalized_mobile = normalize_mobile(mobile)
                if not validate_bangladesh_mobile(normalized_mobile):
                    errors.append("Invalid Bangladeshi mobile number")
                else:
                    mobile = normalized_mobile
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # Store pending registration
                st.session_state.pending_registration = {
                    'account_type': 'individual',
                    'full_name': full_name.strip(),
                    'username': username.strip(),
                    'email': user_info['email'],
                    'mobile': mobile if mobile else '',
                    'phone': phone,
                    'specialization': specialization,
                    'years_experience': years_experience,
                    'is_google_user': True,
                    'google_id': user_info.get('google_id'),
                    'password': None  # No password needed for Google users
                }
                
                # Skip OTP for Google users since they're already verified by Google
                st.session_state.verification_step = 'email_otp'
                st.session_state.verification_contact = user_info['email']
                st.session_state.verification_purpose = 'google_registration'
                st.session_state.temp_otp_code = 'GOOGLE_VERIFIED'
                
                st.success("✅ Google account verified! Completing registration...")
                complete_registration()
                st.rerun()



def complete_registration():
    """Complete the registration process for Google users"""
    from modules.auth import complete_registration as auth_complete_registration
    return auth_complete_registration()


def get_oidc_component():
    """Legacy function - returns None as we're using built-in OIDC"""
    return None

def process_oidc_user():
    """Process OIDC user after successful authentication"""
    
    print("=" * 60)
    print("🔍 PROCESS_OIDC_USER CALLED")
    print("=" * 60)
    
    try:
        # Check if st.user exists and has data
        if not hasattr(st, 'user'):
            print("❌ st.user does not exist")
            return None
        
        print(f"🔍 st.user: {st.user}")
        
        # Try to get user info
        try:
            user_dict = dict(st.user) if st.user else {}
            print(f"🔍 st.user as dict: {user_dict}")
            email = user_dict.get('email')
        except Exception as e:
            print(f"⚠️ Could not read st.user: {e}")
            # Check if we have a code in URL (still processing)
            if 'code' in st.query_params:
                print("⏳ Code in URL - waiting for OIDC to complete...")
                return None
            email = None
        
        # If no email, check if we have a code (still processing)
        if not email:
            if 'code' in st.query_params:
                print("⏳ OIDC callback in progress, waiting for user data...")
                return None
            else:
                print("❌ No email in OIDC user data and no code")
                return None
        
        print(f"✅ Processing OIDC user: {email}")
        
        # Check if user exists in database
        from database.unified_db_manager import UnifiedDatabaseManager
        db = UnifiedDatabaseManager()
        existing_user = db.get_user_by_email(email)
        
        print(f"🔍 Existing user found: {existing_user is not None}")
        
        if existing_user:
            print(f"✅ Existing user: {existing_user.get('username')} (ID: {existing_user.get('id')})")
            
            # Log the user in
            from modules.auth import login_user
            login_success = login_user(existing_user, None, True)
            
            if login_success:
                print(f"✅ OIDC user logged in: {email}")
                print(f"   Session state - logged_in: {st.session_state.get('logged_in')}")
                print(f"   Session state - user_role: {st.session_state.get('user_role')}")
                print(f"   Session state - page before redirect: {st.session_state.get('page')}")
                return {'logged_in': True, 'user_id': existing_user['id']}
            else:
                print(f"❌ Failed to login OIDC user: {email}")
                return None
        else:
            # New user - store for registration
            print(f"🔄 New OIDC user: {email}")
            st.session_state['google_user_info'] = {
                'email': email,
                'name': user_dict.get('name', email.split('@')[0]),
                'sub': user_dict.get('sub', ''),
                'picture': user_dict.get('picture', '')
            }
            st.session_state['show_google_registration'] = True
            print(f"🔍 Stored google_user_info: {st.session_state['google_user_info']}")
            return {'show_registration': True}
            
    except Exception as e:
        print(f"❌ Error processing OIDC user: {e}")
        import traceback
        traceback.print_exc()
        return None