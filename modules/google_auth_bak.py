"""
Google OAuth Authentication Module
Simple Google Sign-In for TenderAI
"""

import streamlit as st
import requests
import json
from datetime import datetime
import hashlib
import secrets
import os
from config import debug_print
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()


def get_google_credentials():
    """Get Google OAuth credentials from secrets"""
    try:
        # Try to get from st.secrets (Streamlit Cloud)
        client_id = st.secrets["GOOGLE_CLIENT_ID"]
        client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
    except:
        # Fallback to environment variables (local development)
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    return client_id, client_secret

# Get credentials
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET = get_google_credentials()

def get_redirect_uri():
    """Get the correct redirect URI dynamically"""
    # Priority 1: From secrets (recommended)
    try:
        if "auth" in st.secrets and "redirect_uri" in st.secrets["auth"]:
            return st.secrets["auth"]["redirect_uri"]
    except:
        pass
    
    # Priority 2: Streamlit Cloud detection
    if os.getenv("STREAMLIT_SHARE") or "streamlit.app" in os.getenv("STREAMLIT_SERVER_HEADLESS", ""):
        return "https://itender-bd.streamlit.app/oauth2callback"
    
    # Priority 3: Local
    return "http://localhost:8501/oauth2callback"

def get_redirect_uri_bak():
    """Get the correct redirect URI for the current environment"""
    # Check if running on Streamlit Cloud
    if 'STREAMLIT_SERVER_PORT' in os.environ:
        return "https://itender-bd.streamlit.app/oauth2callback"
    else:
        return "http://localhost:8501/oauth2callback"

def get_google_auth_url():
    """Generate Google OAuth URL"""
    import urllib.parse
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': get_redirect_uri(),
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return auth_url

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    import urllib.parse
    
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': get_redirect_uri(),
        'grant_type': 'authorization_code'
    }
    
    response = requests.post('https://oauth2.googleapis.com/token', data=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to get token: {response.text}")
        return None

def get_user_info(access_token):
    """Get user information from Google"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to get user info: {response.text}")
        return None

def generate_username_from_email(email):
    """Generate username from email"""
    username = email.split('@')[0]
    # Clean username (remove special characters)
    username = ''.join(c for c in username if c.isalnum() or c == '_')
    # Add random suffix if needed
    return username + secrets.token_hex(2)[:4]

def handle_google_callback():
    """Handle Google OAuth callback from URL parameters"""
    
    # Get code from query parameters
    params = st.query_params
    
    if 'code' not in params:
        return None  # Not a callback
    
    code = params['code']
    
    with st.spinner("Authenticating with Google..."):
        token_data = exchange_code_for_token(code)
        
        if token_data and 'access_token' in token_data:
            user_info = get_user_info(token_data['access_token'])
            
            if user_info:
                email = user_info.get('email')
                name = user_info.get('name', email.split('@')[0])
                
                from database.unified_db_manager import UnifiedDatabaseManager
                import bcrypt
                import secrets
                
                db = UnifiedDatabaseManager()
                
                # Check if user exists
                existing_user = db.get_user_by_email(email)
                
                if existing_user:
                    # Return user data for session restoration
                    return {
                        'logged_in': True,
                        'user_id': existing_user['id'],
                        'username': existing_user['username'],
                        'user_email': email,
                        'full_name': existing_user['full_name'] or name,
                        'user_role': existing_user.get('role', 'individual'),
                        'account_type': existing_user.get('account_type', 'individual'),
                        'company_id': existing_user['company_id'],
                        'page': 'dashboard'
                    }
                else:
                    # Create new individual account
                    try:
                        # Create individual company
                        company_data = {
                            'company_name': f"{name} - Individual Consultant",
                            'email': email,
                            'phone': '',
                            'division': 'Consultant',
                            'is_individual': True
                        }
                        
                        success, company_id = db.create_company(company_data)
                        
                        if success and company_id:
                            # Generate random password
                            temp_password = secrets.token_urlsafe(12)
                            hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            
                            # Generate unique username
                            username = email.split('@')[0]
                            base_username = username
                            counter = 1
                            while db.get_user_by_username(username):
                                username = f"{base_username}{counter}"
                                counter += 1
                            
                            # Create user
                            user_data = {
                                'username': username,
                                'password': hashed_password,
                                'email': email,
                                'full_name': name,
                                'phone': '',
                                'role': 'individual',
                                'account_type': 'individual',
                                'specialization': 'Consultant',
                                'years_experience': 0,
                                'is_approved': True,
                                'auth_provider': 'google'
                            }
                            
                            user_success, user_id = db.create_user(company_id, user_data, 'individual')
                            
                            if user_success:
                                return {
                                    'logged_in': True,
                                    'user_id': user_id,
                                    'username': username,
                                    'user_email': email,
                                    'full_name': name,
                                    'user_role': 'individual',
                                    'account_type': 'individual',
                                    'company_id': company_id,
                                    'company_name': company_data['company_name'],
                                    'page': 'dashboard'
                                }
                            else:
                                st.error(f"Failed to create user: {user_id}")
                        else:
                            st.error(f"Failed to create company: {success}")
                            
                    except Exception as e:
                        st.error(f"Error creating account: {str(e)}")
                
                # Clear query params
                st.query_params.clear()
    
    return None


def render_google_login_button():
    """Render Google Sign-In button"""
    
    st.markdown("""
    <style>
    .google-btn {
        background-color: #ffffff;
        color: #757575;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 10px 16px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        transition: background-color 0.2s, box-shadow 0.2s;
        width: 100%;
    }
    .google-btn:hover {
        background-color: #f5f5f5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .google-icon {
        width: 18px;
        height: 18px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    auth_url = get_google_auth_url()
    
    # HTML button that redirects to Google
    st.markdown(f"""
    <a href="{auth_url}" target="_self" style="text-decoration: none;">
        <div class="google-btn">
            <svg class="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
        </div>
    </a>
    """, unsafe_allow_html=True)

def render_google_registration_form():
    """Render registration completion form for Google users"""
    
    st.markdown("### Complete Your Registration")
    st.info("Welcome! Please complete your account setup.")
    
    user_info = st.session_state.get('pending_google_signup', {})
    
    if not user_info:
        st.error("Session expired. Please try again.")
        st.session_state.show_google_registration = False
        return
    
    with st.form("google_registration_form"):
        st.text_input("Email", value=user_info.get('email', ''), disabled=True)
        full_name = st.text_input("Full Name", value=user_info.get('name', ''), key="google_full_name")
        username = st.text_input("Username", value=user_info.get('email', '').split('@')[0], key="google_username")
        phone = st.text_input("Phone (Optional)", key="google_phone")
        specialization = st.selectbox(
            "Specialization",
            ["Construction Consultant", "Bid Analyst", "Quantity Surveyor", 
             "Project Manager", "Civil Engineer", "Architect", "Other"],
            key="google_specialization"
        )
        years_experience = st.slider("Years of Experience", 0, 40, 5, key="google_years")
        
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *", key="google_terms")
        
        submitted = st.form_submit_button("Complete Registration", type="primary")
        
        if submitted:
            if not all([full_name, username, specialization]):
                st.error("Please fill all required fields")
            elif not terms:
                st.error("Please accept the terms to continue")
            else:
                from database.unified_db_manager import UnifiedDatabaseManager
                import bcrypt
                
                db = UnifiedDatabaseManager()
                
                # Create individual company
                company_data = {
                    'company_name': f"{full_name} - Individual Consultant",
                    'email': user_info['email'],
                    'phone': phone,
                    'division': specialization,
                    'is_individual': True
                }
                
                success, result = db.create_company(company_data)
                
                if success:
                    company_id = result
                    
                    # Generate random password for Google user
                    temp_password = secrets.token_urlsafe(12)
                    hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Create user
                    user_data = {
                        'username': username,
                        'password': hashed_password,
                        'email': user_info['email'],
                        'full_name': full_name,
                        'phone': phone,
                        'role': 'individual',
                        'account_type': 'individual',
                        'specialization': specialization,
                        'years_experience': years_experience,
                        'is_approved': True,
                        'auth_provider': 'google',
                        'google_id': user_info.get('google_id')
                    }
                    
                    user_success, user_result = db.create_user(company_id, user_data, 'individual')
                    
                    if user_success:
                        st.balloons()
                        st.success("Registration successful! You can now login with Google.")
                        
                        st.session_state.show_google_registration = False
                        st.session_state.pending_google_signup = None
                        
                        if st.button("Go to Login", use_container_width=True):
                            st.session_state.page = "individual_login"
                            st.rerun()
                    else:
                        st.error(f"Failed to create user: {user_result}")
                else:
                    st.error(f"Failed to create account: {success}")
def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    client_id, client_secret = get_google_credentials()
    
    if not client_id or not client_secret:
        st.error("❌ Google OAuth not configured")
        return None
    
    redirect_uri = get_redirect_uri()
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post('https://oauth2.googleapis.com/token', data=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get token: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error exchanging code: {str(e)}")
        return None

