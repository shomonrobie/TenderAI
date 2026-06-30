# _pages/login_page.py - Fixed OIDC check

import streamlit as st
from modules.auth import authenticate_user, login_user as auth_login_user, restore_session_from_url

from utils.helpers import navigate_to
from modules.google_auth import render_google_login_button, get_oidc_component
from modules.footer import render_footer
import os

from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()


def show():
    """Login page with Google Sign-In using Streamlit's native OIDC"""
    
    # ========== FORCE ALL TEXT TO BE VISIBLE ==========
    st.markdown("""
    <style>
        /* Force ALL labels to be white */
        label, .stRadio label, .stCheckbox label, 
        .stTextInput label, .stSelectbox label,
        .stRadio label span, .stCheckbox label span,
        div[role="radiogroup"] label, div[role="radiogroup"] label span {
            color: #ffffff !important;
            font-weight: 500 !important;
        }
        
        /* Radio button container */
        .stRadio > div {
            gap: 1rem !important;
        }
        
        /* Radio button labels */
        .stRadio label {
            color: #ffffff !important;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .stRadio label:hover {
            background: rgba(102, 126, 234, 0.15);
            border-color: rgba(102, 126, 234, 0.3);
        }
        
        /* Checkbox labels */
        .stCheckbox label {
            color: #ffffff !important;
        }
        
        .stCheckbox label span {
            color: #ffffff !important;
        }
        
        /* All text inputs labels */
        .stTextInput label, .stSelectbox label {
            color: #ffffff !important;
        }
        
        /* All markdown text */
        .stMarkdown p, .stMarkdown li, .stMarkdown span {
            color: #e0e0e0 !important;
        }
        
        /* Headings */
        h3, h4 {
            color: #e0e0e0 !important;
        }
        
        /* Captions */
        .stCaption {
            color: #94a3b8 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    print("=" * 60)
    print("📄 LOGIN PAGE LOADED")
    print("=" * 60)
    print(f"🔍 logged_in: {st.session_state.get('logged_in', False)}")
    print(f"🔍 page: {st.session_state.get('page', 'None')}")
    print(f"🔍 user_role: {st.session_state.get('user_role', 'None')}")
    
        # ✅ If already logged in, redirect immediately
    if st.session_state.get('logged_in', False):
        user_role = st.session_state.get('user_role', 'viewer')
        print(f"✅ Already logged in as: {user_role}")
        
        if user_role in ['admin', 'system_admin']:
            print("🔀 Redirecting to: admin_dashboard")
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            print("🔀 Redirecting to: company_dashboard")
            navigate_to("company_dashboard")
        else:
            print("🔀 Redirecting to: dashboard")
            navigate_to("dashboard")
        return
    
    # Try to restore session from URL
    print("🔄 Attempting to restore session from URL...")
    if restore_session_from_url():
        user_role = st.session_state.get('user_role', 'viewer')
        print(f"✅ Session restored! Role: {user_role}")
        
        if user_role in ['admin', 'system_admin']:
            print("🔀 Redirecting to: admin_dashboard")
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            print("🔀 Redirecting to: company_dashboard")
            navigate_to("company_dashboard")
        else:
            print("🔀 Redirecting to: dashboard")
            navigate_to("dashboard")
        return
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        print("🔍 Showing Google registration form")
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return

    try:
        if hasattr(st, 'user') and st.user:
            # Try to get email - this will be populated after OIDC callback
            email = st.user.get('email')
            
            if email:
                print(f"✅ OIDC user detected in login page: {email}")
                
                # Process the OIDC user
                from modules.google_auth import process_oidc_user
                result = process_oidc_user()
                
                if result:
                    if result.get('logged_in'):
                        user_role = st.session_state.get('user_role', 'viewer')
                        if user_role in ['admin', 'system_admin']:
                            navigate_to("admin_dashboard")
                        elif user_role == 'company_admin':
                            navigate_to("company_dashboard")
                        else:
                            navigate_to("dashboard")
                        return
                    elif result.get('show_registration'):
                        st.session_state.show_google_registration = True
            else:
                print("ℹ️ No email in st.user yet - waiting for OIDC callback")
    except Exception as e:
        print(f"ℹ️ OIDC check: {e}")
        pass
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    # ========== HANDLE OIDC AUTHENTICATION ==========
    # Check if user is authenticated via Streamlit's OIDC
    # Use try/except to handle different Streamlit versions
    # try:
    #     # Debug: Check if st.user exists
    #     print("🔍 DEBUG: Checking st.user...")
    #     print(f"🔍 hasattr(st, 'user'): {hasattr(st, 'user')}")
        
    #     if hasattr(st, 'user'):
    #         print(f"🔍 st.user value: {st.user}")
    #         print(f"🔍 st.user type: {type(st.user)}")
            
    #         if st.user:
    #             print("🔍 st.user is not empty")
    #             print(f"🔍 st.user keys: {st.user.keys() if hasattr(st.user, 'keys') else 'No keys'}")
                
    #             # Get user info
    #             email = st.user.get('email')
    #             name = st.user.get('name', email.split('@')[0] if email else '')
                
    #             print(f"🔍 Email: {email}")
    #             print(f"🔍 Name: {name}")
    #             print(f"🔍 Sub: {st.user.get('sub')}")
                
    #             if email:
    #                 print(f"✅ OIDC user detected: {email}")
                    
    #                 # Check if user exists in database
    #                 print(f"🔍 Checking database for user with email: {email}")
    #                 google_user = db.get_user_by_email(email)
    #                 print(f"🔍 Database user found: {google_user is not None}")
                    
    #                 if google_user:
    #                     print(f"✅ Existing user found: {google_user.get('username')}")
    #                     print(f"🔍 User role: {google_user.get('role')}")
    #                     print(f"🔍 User ID: {google_user.get('id')}")
                        
    #                     # Existing user - log them in
    #                     print("🔍 Attempting to login user...")
    #                     if auth_login_user(google_user, None, True):  # Remember me for OIDC users
    #                         print("✅ Login successful!")
    #                         st.success(f"Welcome back, {google_user.get('full_name', name)}! 🎉")
    #                         user_role = google_user.get('role', 'viewer')
    #                         print(f"🔍 User role after login: {user_role}")
                            
    #                         # Clear OIDC state after successful login
    #                         if hasattr(st, 'user'):
    #                             print("🔍 Clearing st.user state...")
    #                             # Force session to recognize login
    #                             st.session_state.logged_in = True
    #                             st.session_state.user_id = google_user['id']
    #                             st.session_state.user_role = user_role
    #                             st.session_state.user_name = google_user.get('full_name', name)
                            
    #                         # Redirect to appropriate dashboard
    #                         print(f"🔍 Redirecting to dashboard for role: {user_role}")
    #                         if user_role in ['admin', 'system_admin']:
    #                             print("🔀 Redirecting to: admin_dashboard")
    #                             navigate_to("admin_dashboard")
    #                         elif user_role == 'company_admin':
    #                             print("🔀 Redirecting to: company_dashboard")
    #                             navigate_to("company_dashboard")
    #                         else:
    #                             print("🔀 Redirecting to: dashboard")
    #                             navigate_to("dashboard")
    #                         return
    #                     else:
    #                         print("❌ Login failed!")
    #                         st.error("Failed to login. Please try again.")
    #                 else:
    #                     # New user - show registration form
    #                     print(f"🔄 New user detected, showing registration form")
    #                     print(f"🔍 Setting google_user_info: {email}, {name}")
    #                     st.session_state['google_user_info'] = {
    #                         'email': email,
    #                         'name': name,
    #                         'sub': st.user.get('sub', ''),
    #                         'picture': st.user.get('picture', '')
    #                     }
    #                     st.session_state['show_google_registration'] = True
    #                     print("🔍 Google registration form will be shown")
    #             else:
    #                 print("❌ No email found in st.user")
    #         else:
    #             print("❌ st.user is empty")
    #     else:
    #         print("❌ st.user does not exist")
            
    # except Exception as e:
    #     print(f"❌ OIDC check error: {e}")
    #     import traceback
    #     traceback.print_exc()
    #     pass
    
    # ========== PAGE STYLES ==========
    st.markdown("""
    <style>    
    /* Page Background Gradient - Aggressive Override */
    html, body,
    .stApp, 
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > section,
    [data-testid="stAppViewContainer"] > section > div,
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stAppViewContainer"] > .main .block-container {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 60%, #0a0a1a 100%) !important;
        background-color: #0a0a1a !important;
    }
    
    /* Force transparent on intermediate containers */
    [data-testid="stAppViewContainer"] > section > div,
    [data-testid="stAppViewContainer"] > section > div > div,
    .main .block-container > div {
        background: transparent !important;
    }
    .login-container .stVerticalBlock {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    .branding-container .stVerticalBlock {
        background: linear-gradient(145deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        border: 1px solid rgba(102, 126, 234, 0.1);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    /* Main container */
    .login-main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem 2rem;
    }
    
    .login-header {
        text-align: center;
        padding: 1rem 0 1.5rem 0;
    }
    
    .login-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    .login-header p {
        color: #94a3b8;
        font-size: 1.1rem;
    }
    
    .login-box {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .login-box h3 {
        color: #e0e0e0;
        margin-bottom: 1.5rem;
    }
    
    .branding-box {
        background: linear-gradient(145deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        border: 1px solid rgba(102, 126, 234, 0.1);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .branding-box .logo-placeholder {
        font-size: 5rem;
        margin-bottom: 1rem;
    }
    
    .branding-box h3 {
        color: #e0e0e0;
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .branding-box p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0.5rem 0;
    }
    
    .branding-box .tagline {
        color: #64748b;
        font-size: 0.85rem;
    }
    
    .feature-list {
        text-align: left;
        margin-top: 1.5rem;
        padding: 0;
    }
    
    .feature-list li {
        color: #94a3b8;
        font-size: 0.85rem;
        padding: 0.3rem 0;
        list-style: none;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .feature-list li::before {
        content: '✓';
        color: #667eea;
        font-weight: bold;
        font-size: 1rem;
    }
    
    .or-divider {
        text-align: center;
        color: #64748b;
        font-size: 0.9rem;
        margin: 1.5rem 0 1rem 0;
        position: relative;
    }
    
    .or-divider::before,
    .or-divider::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 35%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.2));
    }
    
    .or-divider::before {
        left: 0;
    }
    
    .or-divider::after {
        right: 0;
        background: linear-gradient(90deg, rgba(102, 126, 234, 0.2), transparent);
    }
    
    .login-footer-text {
        text-align: center;
        color: #64748b;
        font-size: 0.75rem;
        margin-top: 0.5rem;
    }
    
    .login-footer-text a {
        color: #667eea;
        text-decoration: none;
    }
    
    .login-footer-text a:hover {
        text-decoration: underline;
    }
    
    .google-btn-container {
        display: flex;
        justify-content: center;
        margin: 0.5rem 0;
    }
    
    /* Form styling */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #e0e0e0 !important;
        border-radius: 8px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
    }
    
    .stCheckbox label {
        color: #94a3b8 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    
    /* Success/Error messages */
    .stAlert {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
    }
    
    @media (max-width: 768px) {
        .login-main-container {
            padding: 0.5rem 1rem;
        }
        .branding-box {
            margin-top: 1rem;
            padding: 1.5rem;
        }
        .login-box {
            padding: 1.5rem;
        }
        .login-header h1 {
            font-size: 2rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ========== MAIN CONTENT ==========
    st.markdown('<div class="login-main-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="login-header">
        <h1>🔐 Welcome to TenderAI</h1>
        <p>Bangladesh's First AI-Powered Tender Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== TWO COLUMN LAYOUT ==========
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        # Use st.container() to properly wrap widgets
        with st.container():
            # Inject CSS to style this specific container
            st.markdown("""
            <style>
            /* Target the container inside col1 */
            div[data-testid="stColumn"]:nth-child(1) .stContainer .stVerticalBlock {
                background: rgba(255, 255, 255, 0.03);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 2rem;
                border: 1px solid rgba(102, 126, 234, 0.1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("### 👤 Login to Your Account")
            
            # ========== LOGIN FORM ==========
            with st.form("login_form"):
                username = st.text_input(
                    "Username or Email", 
                    placeholder="Enter your username or email",
                    key="login_username"
                )
                password = st.text_input(
                    "Password", 
                    type="password", 
                    placeholder="Enter your password",
                    key="login_password"
                )
                remember_me = st.checkbox(
                    "Remember me (stay logged in for 30 days)",
                    key="remember_me"
                )
                
                submitted = st.form_submit_button(
                    "🔓 Sign In", 
                    type="primary", 
                    use_container_width=True
                )
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        user = authenticate_user(username, password)
                        
                        if user:
                            if auth_login_user(user, password, remember_me):
                                st.success(f"Welcome back, {user.get('full_name', user.get('username'))}! 🎉")
                                user_role = user.get('role', 'viewer')
                                if user_role in ['admin', 'system_admin']:
                                    navigate_to("admin_dashboard")
                                elif user_role == 'company_admin':
                                    navigate_to("company_dashboard")
                                else:
                                    navigate_to("dashboard")
                                return
                            else:
                                st.error("Login failed")
                        else:
                            st.error("Invalid username/email or password")
            
            # ========== DIVIDER AND GOOGLE SIGN-IN ==========
            st.markdown('<div class="or-divider">OR</div>', unsafe_allow_html=True)
            
            st.markdown("""
            <div style="text-align: center;">
                <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.5rem;">
                    Sign in with your Google account
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col_google1, col_google2, col_google3 = st.columns([1, 2, 1])
            with col_google2:
                # Use the render function from google_auth module
                render_google_login_button(registration_mode=False)
            
            st.markdown("""
            <div class="login-footer-text">
                By continuing, you agree to our 
                <a href="?page=terms">Terms of Service</a> and 
                <a href="?page=privacy">Privacy Policy</a>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📝 Register", use_container_width=True):
                    navigate_to("register")
                    st.rerun()
            with col_b:
                if st.button("🔒 Forgot Password?", use_container_width=True):
                    navigate_to("forgot_password")
                    st.rerun()

    with col2:
        # Use st.container() for branding box
        with st.container():
            st.markdown("""
            <style>
            /* Target the container inside col2 */
            div[data-testid="stColumn"]:nth-child(2) .stContainer .stVerticalBlock {
                background: linear-gradient(145deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                border: 1px solid rgba(102, 126, 234, 0.1);
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Try to display logo
            logo_paths = [
                "assets/images/tender_ai_logo.jpg",
                "assets/images/tender_ai_logo.png",
                "assets/images/logo.jpg",
                "assets/images/logo.png"
            ]
            
            logo_found = False
            for path in logo_paths:
                if os.path.exists(path):
                    st.image(path, use_container_width=True)
                    logo_found = True
                    break
            
            if not logo_found:
                st.markdown('<div class="logo-placeholder">🏗️</div>', unsafe_allow_html=True)
            
            st.markdown("""
            <h3>Smart Tender Intelligence</h3>
            <p class="tagline">AI-Powered • Data-Driven • Results-Focused</p>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <ul class="feature-list">
                <li>AI-powered bid optimization</li>
                <li>Real-time win probability analysis</li>
                <li>Competitor intelligence & tracking</li>
                <li>Automated BOQ generation</li>
                <li>Historical tender insights</li>
                <li>e-GP integration ready</li>
            </ul>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; margin-top: 1rem;">
                <span style="background: rgba(102, 126, 234, 0.1); padding: 0.2rem 0.8rem; border-radius: 12px; color: #94a3b8; font-size: 0.7rem; border: 1px solid rgba(102, 126, 234, 0.1);">
                    🤖 AI Powered
                </span>
                <span style="background: rgba(102, 126, 234, 0.1); padding: 0.2rem 0.8rem; border-radius: 12px; color: #94a3b8; font-size: 0.7rem; border: 1px solid rgba(102, 126, 234, 0.1);">
                    📊 e-GP Ready
                </span>
                <span style="background: rgba(102, 126, 234, 0.1); padding: 0.2rem 0.8rem; border-radius: 12px; color: #94a3b8; font-size: 0.7rem; border: 1px solid rgba(102, 126, 234, 0.1);">
                    🔒 SSL Secure
                </span>
                <span style="background: rgba(102, 126, 234, 0.1); padding: 0.2rem 0.8rem; border-radius: 12px; color: #94a3b8; font-size: 0.7rem; border: 1px solid rgba(102, 126, 234, 0.1);">
                    🇧🇩 Made in BD
                </span>
            </div>
            """, unsafe_allow_html=True)
    # If we have an OIDC user but somehow got here, redirect
    if hasattr(st, 'user') and st.user:
        try:
            user_dict = dict(st.user) if st.user else {}
            email = user_dict.get('email')
            if email:
                print(f"🔄 OIDC user detected on login page: {email}")
                from modules.google_auth import process_oidc_user
                result = process_oidc_user()
                if result and result.get('logged_in'):
                    user_role = st.session_state.get('user_role', 'viewer')
                    if user_role in ['admin', 'system_admin']:
                        navigate_to("admin_dashboard")
                    elif user_role == 'company_admin':
                        navigate_to("company_dashboard")
                    else:
                        navigate_to("dashboard")
                    return
        except:
            pass
    # ========== FOOTER ==========
    st.markdown("---")
    render_footer()