# modules/google_auth.py - Using Streamlit's built-in OIDC
import streamlit as st
import os
from datetime import datetime
from database.unified_db_manager import get_db_manager
import logging

from utils.validators import validate_bangladesh_mobile, normalize_mobile
from utils.helpers import navigate_to

logger = logging.getLogger(__name__)
_db = None

def get_db():
    global _db
    if _db is None:
        _db = get_db_manager()
    return _db



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
    db = get_db()
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
    """Render registration completion form for Google users with OTP verification"""
    
    print("🔍 RENDER_GOOGLE_REGISTRATION_FORM CALLED")
    
    # Check if we have an existing user ID from process_oidc_user
    existing_user_id = st.session_state.get('existing_google_user_id')
    
    # Try both session variables for user info
    user_info = st.session_state.get('pending_google_signup') or st.session_state.get('google_user_info')
    
    print(f"🔍 user_info: {user_info}")
    
    if not user_info:
        st.error("Session expired. Please try again.")
        st.session_state.show_google_registration = False
        st.rerun()
        return
    
    # Check if user already exists in database
    email = user_info.get('email')
    if email and not existing_user_id:
        existing_user = db_instance.get_user_by_email(email)
        if existing_user:
            existing_user_id = existing_user.get('id')
            print(f"✅ Existing user found: {existing_user_id}")
    
    # ========== CSS STYLES ==========
    st.markdown("""
    <style>
        .stTextInput label, .stSelectbox label, .stCheckbox label {
            color: #333333 !important;
            font-weight: 500 !important;
        }
        .stTextInput input:disabled {
            color: #666666 !important;
            opacity: 0.8 !important;
        }
        .stTextInput input::placeholder {
            color: #999999 !important;
        }
        .stMarkdown h3, .stMarkdown h4 {
            color: #333333 !important;
        }
        .stMarkdown p, .stMarkdown li, .stMarkdown span {
            color: #333333 !important;
        }
        .stAlert .stMarkdown p {
            color: #333333 !important;
        }
        .stCaption {
            color: #666666 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ========== CHECK IF USER ALREADY COMPLETED REGISTRATION ==========
    if existing_user_id:
        user = db_instance.get_user_by_id(existing_user_id)
        if user and user.get('registration_complete', False):
            st.success(f"✅ Welcome back, {user.get('full_name', user_info.get('name'))}!")
            from modules.auth import login_user
            if login_user(user, None, True):
                st.session_state.show_google_registration = False
                user_role = st.session_state.get('user_role', 'viewer')
                if user_role in ['admin', 'system_admin']:
                    navigate_to("admin_dashboard")
                elif user_role == 'company_admin':
                    navigate_to("company_dashboard")
                else:
                    navigate_to("dashboard")
                return
    
    # ========== REGISTRATION FORM ==========
    st.markdown("### ✅ Complete Your Registration with Google")
    
    if existing_user_id:
        st.info(f"👋 Welcome back, **{user_info.get('name', '')}**! Please complete your registration.")
    else:
        st.info(f"👋 Welcome **{user_info.get('name', '')}**! Please complete your registration.")
    
    with st.form("google_registration_form"):
        # Pre-filled fields from Google
        st.text_input("Email", value=user_info.get('email', ''), disabled=True)
        full_name = st.text_input("Full Name *", value=user_info.get('name', ''))
        username = st.text_input("Username *", value=user_info.get('email', '').split('@')[0])
        
        st.markdown("---")
        st.markdown("#### Contact Information")
        
        mobile = st.text_input(
            "Mobile Number *", 
            placeholder="01XXXXXXXXX (11 digits)",
            help="Enter your 11-digit Bangladeshi mobile number starting with 01 (e.g., 017XXXXXXXX)"
        )
        phone = st.text_input("Phone (Alternative)", placeholder="Your phone number")
        
        st.markdown("---")
        st.markdown("#### Professional Information (Optional)")
        
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
            
            # Validate full name
            if not full_name or not full_name.strip():
                errors.append("Full name is required")
            
            # Validate username
            if not username or not username.strip():
                errors.append("Username is required")
            elif len(username) < 3:
                errors.append("Username must be at least 3 characters")
            
            # Validate mobile number
            if not mobile or not mobile.strip():
                errors.append("Mobile number is required")
            else:
                normalized_mobile = normalize_mobile(mobile)
                if not validate_bangladesh_mobile(normalized_mobile):
                    errors.append("Invalid Bangladeshi mobile number. Must be 11 digits starting with 01")
                else:
                    mobile = normalized_mobile
                    
                    # Check if mobile number already exists
                    try:
                        existing_mobile_user = db_instance.query_one(
                            "SELECT id FROM users WHERE mobile_number = ? AND id != ?", 
                            (mobile, existing_user_id or 0)
                        )
                        if existing_mobile_user:
                            errors.append(f"This mobile number ({mobile}) is already registered. Please use a different mobile number.")
                    except Exception as e:
                        print(f"⚠️ Error checking mobile number: {e}")
            
            # Validate terms
            if not terms:
                errors.append("You must agree to the Terms of Service and Privacy Policy")
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # Store pending registration data
                pending_data = {
                    'account_type': 'individual',
                    'full_name': full_name.strip(),
                    'username': username.strip(),
                    'email': user_info['email'],
                    'mobile': mobile,
                    'phone': phone if phone else '',
                    'specialization': specialization,
                    'years_experience': years_experience,
                    'is_google_user': True,
                    'google_id': user_info.get('google_id') or user_info.get('sub', ''),
                    'password': None
                }
                
                st.session_state.pending_registration = pending_data
                
                # ✅ If user already exists, update directly (no OTP needed)
                if existing_user_id:
                    try:
                        db_instance.execute("""
                            UPDATE users 
                            SET full_name = ?, username = ?, mobile_number = ?,
                                specialization = ?, years_experience = ?,
                                registration_complete = TRUE,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (
                            full_name.strip(),
                            username.strip(),
                            mobile,
                            specialization,
                            years_experience,
                            existing_user_id
                        ))
                        
                        st.success("✅ Registration completed successfully!")
                        st.balloons()
                        
                        # Clear session flags
                        st.session_state.show_google_registration = False
                        st.session_state.pending_google_signup = None
                        st.session_state.google_user_info = None
                        
                        # Login the user
                        user = db_instance.get_user_by_id(existing_user_id)
                        if user:
                            from modules.auth import login_user
                            if login_user(user, None, True):
                                user_role = st.session_state.get('user_role', 'viewer')
                                if user_role in ['admin', 'system_admin']:
                                    navigate_to("admin_dashboard")
                                elif user_role == 'company_admin':
                                    navigate_to("company_dashboard")
                                else:
                                    navigate_to("dashboard")
                                return
                        return
                        
                    except Exception as e:
                        st.error(f"Error completing registration: {e}")
                        return
                
                # ✅ New user - send OTP for email verification
                from utils.otp_service import OTPService
                otp_service = OTPService(db_instance)
                success, message, otp_code = otp_service.send_verification_otp(
                    contact_type='email',
                    contact_value=user_info['email'],
                    target_type='user',
                    target_id=0,
                    purpose='registration'
                )
                
                if success:
                    st.session_state.verification_step = 'email_otp'
                    st.session_state.verification_contact = user_info['email']
                    st.session_state.verification_purpose = 'registration'
                    st.session_state.temp_otp_code = otp_code
                    st.session_state.pending_registration = pending_data
                    st.session_state.show_google_registration = False
                    st.session_state.pending_google_signup = None
                    st.session_state.google_user_info = None
                    
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def get_oidc_component():
    """Legacy function - returns None as we're using built-in OIDC"""
    return None
def handle_google_callback():
    """Handle Google OAuth callback using Streamlit's built-in OIDC"""
    db = get_db()
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


def complete_registration():
    """Complete the registration process for Google users"""    
    from _pages.registration_page import complete_registration as reg_complete
    reg_complete()
    st.rerun()
    return

   


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
            name = user_dict.get('name', email.split('@')[0] if email else 'Unknown')
            google_sub = user_dict.get('sub', '')
            google_picture = user_dict.get('picture', '')
            email_verified = user_dict.get('email_verified', False)
        except Exception as e:
            print(f"⚠️ Could not read st.user: {e}")
            if 'code' in st.query_params:
                print("⏳ Code in URL - waiting for OIDC to complete...")
                return None
            email = None
        
        if not email:
            if 'code' in st.query_params:
                print("⏳ OIDC callback in progress, waiting for user data...")
                return None
            else:
                print("❌ No email in OIDC user data and no code")
                return None
        
        print(f"✅ Processing OIDC user: {email}")
        print(f"   Name: {name}")
        print(f"   Google Sub: {google_sub}")
        print(f"   Email Verified: {email_verified}")
        
        db = get_db()
        
        # ✅ FIRST: Check if user exists by email
        print("🔍 Checking if user exists...")
        existing_user = db.get_user_by_email(email)
        
        if existing_user:
            print(f"✅ Existing user found: {existing_user.get('username')} (ID: {existing_user.get('id')})")
            
            # ✅ CHECK AUTH PROVIDER - THIS IS THE FIX
            auth_provider = existing_user.get('auth_provider', 'email_password')
            print(f"🔍 Auth Provider: {auth_provider}")
            
            registration_complete = existing_user.get('registration_complete', 0)
            print(f"   Registration complete: {registration_complete}")
            
            # ✅ If user exists but registration not complete - show registration form
            if not registration_complete or registration_complete == 0:
                print("🔄 User exists but registration incomplete - showing registration form")
                st.session_state['google_user_info'] = {
                    'email': email,
                    'name': name,
                    'sub': google_sub,
                    'picture': google_picture
                }
                st.session_state['show_google_registration'] = True
                return {'show_registration': True, 'existing_user': existing_user}
            
            # ============================================================
            # ✅ GOOGLE OAUTH USERS: Skip 2FA completely
            # ============================================================
            if auth_provider == 'google':
                print(f"✅ Google OAuth user - SKIPPING 2FA")
                
                # Login directly
                from modules.auth import _complete_login
                if _complete_login(existing_user, True):
                    print(f"✅ Google user logged in directly: {email}")
                    return {'logged_in': True, 'user_id': existing_user['id']}
                else:
                    print(f"❌ Failed to login Google user")
                    return None
            
            # ============================================================
            # EMAIL/PASSWORD USERS: Require 2FA
            # ============================================================
            print(f"🔐 Email/password user - requiring 2FA")
            
            # ✅ Check if already logged in
            if st.session_state.get('logged_in', False) and st.session_state.get('user_id') == existing_user.get('id'):
                print("✅ User already logged in - skipping 2FA")
                return {'logged_in': True, 'user_id': existing_user['id']}
            
            # ✅ Check if 2FA is already verified in this session
            if st.session_state.get('two_factor_verified', False):
                print("✅ 2FA already verified in this session - logging in")
                from modules.auth import _complete_login
                login_success = _complete_login(existing_user, True)
                if login_success:
                    return {'logged_in': True, 'user_id': existing_user['id']}
                else:
                    return None
            
            # ✅ Check if we're already in 2FA verification step
            if st.session_state.get('verification_step') == '2fa_otp':
                print("⏳ Already in 2FA verification - waiting for user input")
                return {'requires_2fa': True, 'user_id': existing_user['id']}
            
            # ✅ User registration complete - send 2FA OTP
            print("✅ User registration complete - sending 2FA OTP")
            
            # ✅ Store user data and send OTP
            st.session_state.pending_2fa_user_id = existing_user['id']
            st.session_state.pending_2fa_user_data = existing_user
            st.session_state.verification_step = '2fa_otp'
            
            # Send OTP
            from utils.otp_service import OTPService
            otp_service = OTPService(db)
            success, message, otp_code = otp_service.send_verification_otp(
                contact_type='email',
                contact_value=email,
                target_type='user',
                target_id=existing_user['id'],
                purpose='2fa_login'
            )
            
            if success:
                st.session_state._2fa_otp_sent = True
                st.session_state._2fa_otp_code = otp_code
                st.session_state._2fa_contact = email
                print(f"✅ 2FA OTP sent to: {email}")
                return {'requires_2fa': True, 'user_id': existing_user['id']}
            else:
                print(f"❌ Failed to send 2FA OTP: {message}")
                return None
        
        # ✅ User does NOT exist - create new user
        print("🔄 No existing user found - creating new user")
        
        username = email.split('@')[0]
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        user_data = {
            'username': username,
            'email': email,
            'full_name': name,
            'google_id': google_sub,
            'picture': google_picture,
            'mobile_number': '',
            'phone': '',
            'auth_provider': 'google',  # ✅ Mark as Google OAuth user
            'email_verified': 1 if email_verified else 0  # ✅ Google verified
        }
        
        print(f"📝 Creating user with data: {user_data}")
        
        success, result = db.create_google_user(user_data)
        
        if success:
            user_id = result
            print(f"✅ User processed successfully! User ID: {user_id}")
            
            existing_user = db.get_user_by_id(user_id)
            
            if existing_user:
                registration_complete = existing_user.get('registration_complete', 0)
                
                if not registration_complete or registration_complete == 0:
                    print("🔄 New user - needs to complete registration")
                    st.session_state['google_user_info'] = {
                        'email': email,
                        'name': name,
                        'sub': google_sub,
                        'picture': google_picture
                    }
                    st.session_state['show_google_registration'] = True
                    return {'show_registration': True, 'new_user': True}
                else:
                    # ✅ Google OAuth user - login directly (no 2FA)
                    from modules.auth import _complete_login
                    login_success = _complete_login(existing_user, True)
                    if login_success:
                        print(f"✅ New Google user logged in directly: {email}")
                        return {'logged_in': True, 'user_id': existing_user['id']}
            else:
                print(f"❌ Could not retrieve user after creation: {user_id}")
                return None
        else:
            error_msg = result
            print(f"❌ Failed to process user: {error_msg}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing OIDC user: {e}")
        import traceback
        traceback.print_exc()
        return None