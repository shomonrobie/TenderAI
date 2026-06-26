# modules/google_auth.py - Updated with debug logging

import streamlit as st
import requests
import json
import os
import secrets
import urllib.parse
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

# =============================================================================
# CREDENTIALS - Lazy Loading
# =============================================================================

_google_client_id = None
_google_client_secret = None

def get_google_credentials():
    """Get Google OAuth credentials from secrets - tries multiple formats"""
    global _google_client_id, _google_client_secret
    
    if _google_client_id:
        return _google_client_id, _google_client_secret
    
    client_id = ""
    client_secret = ""
    
    try:
        client_id = st.secrets["GOOGLE_CLIENT_ID"]
        client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
        print("✅ Found credentials in flat structure")
    except:
        pass
    
    if not client_id:
        try:
            client_id = st.secrets["google"]["client_id"]
            client_secret = st.secrets["google"]["client_secret"]
            print("✅ Found credentials under [google]")
        except:
            pass
    
    if not client_id:
        try:
            client_id = st.secrets["auth"]["google_client_id"]
            client_secret = st.secrets["auth"]["google_client_secret"]
            print("✅ Found credentials under [auth]")
        except:
            pass
    
    if not client_id:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        if client_id:
            print("✅ Found credentials in environment variables")
    
    if client_id:
        _google_client_id = client_id
        _google_client_secret = client_secret
        print(f"✅ Google Client ID: {client_id[:20]}...")
    else:
        print("❌ No Google credentials found!")
    
    return client_id, client_secret

def get_redirect_uri():
    """Get the correct redirect URI - works on both local and cloud"""
    import os
    
    # Priority 1: Check Streamlit Cloud secrets (dashboard)
    try:
        if "redirect_uri" in st.secrets:
            uri = st.secrets["redirect_uri"]
            print(f"✅ Found redirect_uri in Streamlit secrets: {uri}")
            return uri
    except:
        pass
    
    # Priority 2: Check [auth] section
    try:
        if "auth" in st.secrets and "redirect_uri" in st.secrets["auth"]:
            uri = st.secrets["auth"]["redirect_uri"]
            print(f"✅ Found redirect_uri in [auth]: {uri}")
            return uri
    except:
        pass
    
    # Priority 3: Detect environment automatically
    # Streamlit Cloud sets these environment variables
    is_cloud = (
        os.getenv("STREAMLIT_SHARING_MODE") or
        os.getenv("DEPLOYMENT") == "streamlit" or
        "streamlit.app" in os.getenv("HOSTNAME", "") or
        os.path.exists("/home/appuser")  # Streamlit Cloud home directory
    )
    
    if is_cloud:
        uri = "https://itender-bd.streamlit.app/"
        print(f"✅ Detected Streamlit Cloud, using: {uri}")
        return uri
    else:
        uri = "http://localhost:8501/"
        print(f"✅ Local development, using: {uri}")
        return uri
    
def get_google_auth_url():
    """Generate Google OAuth URL"""
    client_id, _ = get_google_credentials()
    
    if not client_id:
        return None
    
    redirect_uri = get_redirect_uri()
    
    # 🔍 DEBUG: Print the exact redirect URI
    print(f"🔍 DEBUG: redirect_uri = '{redirect_uri}'")
    print(f"🔍 DEBUG: Length = {len(redirect_uri)}")
    print(f"🔍 DEBUG: Ends with /? {redirect_uri.endswith('/')}")
    print(f"🔍 DEBUG: Repr = {repr(redirect_uri)}")
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    print(f"🔗 Full Auth URL: {auth_url}")
    return auth_url


def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    client_id, client_secret = get_google_credentials()
    
    print(f"🔑 Exchanging code for token...")
    print(f"   Client ID: {client_id[:20] if client_id else 'MISSING'}...")
    print(f"   Client Secret: {'FOUND' if client_secret else 'MISSING'}")
    
    if not client_id or not client_secret:
        st.error("❌ Google OAuth not configured")
        return None
    
    redirect_uri = get_redirect_uri()
    print(f"   Redirect URI: {redirect_uri}")
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        print("📤 Sending token request...")
        response = requests.post('https://oauth2.googleapis.com/token', data=data, timeout=10)
        
        print(f"📥 Token response status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Token received successfully")
            return token_data
        else:
            print(f"❌ Token error: {response.text}")
            st.error(f"Failed to get token: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Token exchange error: {str(e)}")
        st.error(f"Error exchanging code: {str(e)}")
        return None


def get_user_info(access_token):
    """Get user information from Google"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    print("👤 Getting user info...")
    
    try:
        response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers, timeout=10)
        
        print(f"📥 User info response status: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ User info received: {user_info.get('email')}")
            return user_info
        else:
            print(f"❌ User info error: {response.text}")
            st.error(f"Failed to get user info: {response.text}")
            return None
    except Exception as e:
        print(f"❌ User info error: {str(e)}")
        st.error(f"Error getting user info: {str(e)}")
        return None

# modules/google_auth.py - In handle_google_callback

def handle_google_callback():
    """Handle Google OAuth callback from URL parameters"""
    
    params = st.query_params
    
    if 'code' not in params:
        return None
    
    # ✅ Save the code and immediately clear it from URL
    code = params['code']
    print(f"🔑 Code received: {code[:10]}...")
    
    # ✅ CRITICAL: Clear the code from URL immediately
    # This prevents re-processing on page refresh
    st.query_params.clear()
    
    with st.spinner("Authenticating with Google..."):
        token_data = exchange_code_for_token(code)
        
        if not token_data or 'access_token' not in token_data:
            st.error("❌ Failed to authenticate with Google")
            return None
        
        user_info = get_user_info(token_data['access_token'])
        
        if not user_info:
            st.error("❌ Failed to get user information")
            return None
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists
        existing_user = db.get_user_by_email(email)
        
        if existing_user:
            from modules.auth import login_user
            login_user(existing_user, None, remember_me=True)
            st.success(f"Welcome back, {existing_user.get('full_name', name)}! 🎉")
            
            # ✅ Save session to URL (with remember_me)
            from modules.auth import save_session_to_url
            save_session_to_url(True)
            
            return {'logged_in': True, 'user_id': existing_user['id']}
        else:
            st.session_state.pending_google_signup = {
                'email': email,
                'name': name,
                'google_id': user_info.get('id')
            }
            st.session_state.show_google_registration = True
            return {'show_registration': True}
    
    return None




def render_google_login_button():
    """Render Google Sign-In button"""
    
    client_id, _ = get_google_credentials()
    
    if not client_id:
        st.warning("⚠️ Google Sign-In is not configured. Please contact administrator.")
        return
    
    auth_url = get_google_auth_url()
    
    if not auth_url:
        st.error("❌ Failed to generate login URL")
        return
    
    st.markdown("""
    <style>
    .google-btn {
        background-color: #ffffff;
        color: #757575;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px 20px;
        font-size: 15px;
        font-weight: 500;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        transition: all 0.2s ease;
        width: 100%;
        text-decoration: none;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .google-btn:hover {
        background-color: #f5f5f5;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
        text-decoration: none;
    }
    .google-icon {
        width: 20px;
        height: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
    
    user_info = st.session_state.get('pending_google_signup', {})
    
    if not user_info:
        st.error("Session expired. Please try again.")
        st.session_state.show_google_registration = False
        return
    
    st.markdown("### Complete Your Registration")
    st.info(f"Welcome {user_info.get('name', '')}! Please complete your registration.")
    
    with st.form("google_registration_form"):
        st.text_input("Email", value=user_info.get('email', ''), disabled=True)
        full_name = st.text_input("Full Name", value=user_info.get('name', ''))
        username = st.text_input("Username", value=user_info.get('email', '').split('@')[0])
        phone = st.text_input("Phone (Optional)")
        specialization = st.selectbox(
            "Specialization",
            ["Construction Consultant", "Bid Analyst", "Quantity Surveyor", 
             "Project Manager", "Civil Engineer", "Architect", "Other"]
        )
        years_experience = st.slider("Years of Experience", 0, 40, 5)
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *")
        
        submitted = st.form_submit_button("Complete Registration", type="primary")
        
        if submitted:
            if not all([full_name, username, specialization]):
                st.error("Please fill all required fields")
            elif not terms:
                st.error("Please accept the terms to continue")
            else:
                import bcrypt
                
                company_data = {
                    'company_name': f"{full_name} - Individual Consultant",
                    'email': user_info['email'],
                    'phone': phone,
                    'division': specialization,
                    'is_individual': True
                }
                
                success, company_id = db.create_company(company_data)
                
                if success and company_id:
                    temp_password = secrets.token_urlsafe(12)
                    hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
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
                        st.rerun()
                    else:
                        st.error(f"Failed to create user: {user_result}")
                else:
                    st.error(f"Failed to create account")