# _pages/login_page.py - Complete refactored login page

import streamlit as st
import os
from modules.auth import (
    authenticate_user, 
    login_user as auth_login_user, 
    restore_session_from_url,
    verify_2fa_otp,
    resend_2fa_otp,
    logout_user
)
from utils.helpers import navigate_to
from modules.google_auth import render_google_login_button, process_oidc_user
from modules.footer import render_footer

from database.unified_db_manager import get_db_manager

def mask_email(email: str) -> str:
    """Mask email for display (e.g., j****n@example.com)"""
    if not email:
        return ""
    parts = email.split('@')
    if len(parts) != 2:
        return email
    username, domain = parts
    if len(username) <= 2:
        masked_username = username[0] + '*' * (len(username) - 1)
    else:
        masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
    return f"{masked_username}@{domain}"

def render_2fa_verification():
    """Render 2FA OTP verification screen for login"""
    
    st.markdown("""
    <div style="max-width: 450px; margin: 0 auto; padding: 2rem 1rem;">
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2rem; font-weight: 700; color: #667eea;">🔐 Two-Factor Authentication</h1>
            <p style="color: #94a3b8; font-size: 0.95rem;">Enter the verification code sent to your email</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        contact = st.session_state.get('_2fa_contact', 'your email')
        st.info(f"📧 A verification code has been sent to **{contact}**")
        
        otp = st.text_input(
            "Verification Code",
            type="password",
            max_chars=6,
            placeholder="Enter 6-digit code",
            key="2fa_otp_input",
            label_visibility="collapsed"
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("✅ Verify & Login", type="primary", use_container_width=True):
                if otp and len(otp) == 6:
                    success, message = verify_2fa_otp(otp)
                    if success:
                        st.success("✅ Verification successful! Redirecting...")
                        user_role = st.session_state.get('user_role', 'viewer')
                        if user_role in ['admin', 'system_admin']:
                            navigate_to("admin_dashboard")
                        elif user_role == 'company_admin':
                            navigate_to("company_dashboard")
                        else:
                            navigate_to("dashboard")
                        return
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("Please enter the 6-digit verification code")
        
        with col_b:
            if st.button("🔄 Resend Code", use_container_width=True):
                success, message = resend_2fa_otp()
                if success:
                    st.success("✅ New code sent successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        st.divider()
        if st.button("← Back to Login", use_container_width=True):
            logout_user()
            st.rerun()


def show():
    """Login page with Google Sign-In using Streamlit's native OIDC"""
    
    print("=" * 60)
    print("📄 LOGIN PAGE LOADED")
    print("=" * 60)
    print(f"🔍 logged_in: {st.session_state.get('logged_in', False)}")
    print(f"🔍 page: {st.session_state.get('page', 'None')}")
    print(f"🔍 user_role: {st.session_state.get('user_role', 'None')}")
    
    # ✅ Get db only if needed
    db = get_db_manager()
    
    # ========== CHECK: 2FA VERIFICATION ==========
    if st.session_state.get('verification_step') == '2fa_otp':
        render_2fa_verification()
        return
    
    # ========== CHECK: GOOGLE REGISTRATION ==========
    if st.session_state.get('show_google_registration', False):
        print("🔍 Google registration flag detected - showing registration form")
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    # ========== CHECK: ALREADY LOGGED IN ==========
    if st.session_state.get('logged_in', False):
        print("✅ User already logged in, redirecting...")
        user_role = st.session_state.get('user_role', 'viewer')
        if user_role in ['admin', 'system_admin']:
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            navigate_to("company_dashboard")
        else:
            navigate_to("dashboard")
        return
    
    # ========== RESTORE SESSION FROM URL ==========
    print("🔄 Attempting to restore session from URL...")
    if restore_session_from_url():
        user_role = st.session_state.get('user_role', 'viewer')
        print(f"✅ Session restored! Role: {user_role}")
        
        if user_role in ['admin', 'system_admin']:
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            navigate_to("company_dashboard")
        else:
            navigate_to("dashboard")
        return
    
    # ========== CHECK FOR OIDC CALLBACK ==========
    if 'code' in st.query_params:
        print("🔄 OIDC callback detected on login page")
        if not (hasattr(st, 'user') and st.user):
            print("⏳ Waiting for OIDC callback to complete...")
            st.info("⏳ Completing Google authentication...")
            return
    
    # ========== PROCESS OIDC USER ==========
    try:
        if hasattr(st, 'user') and st.user:
            email = st.user.get('email')
            if email:
                print(f"✅ OIDC user detected in login page: {email}")
                result = process_oidc_user()
                
                if result:
                    if result.get('logged_in'):
                        print(f"✅ OIDC user logged in: {email}")
                        user_role = st.session_state.get('user_role', 'viewer')
                        if user_role in ['admin', 'system_admin']:
                            navigate_to("admin_dashboard")
                        elif user_role == 'company_admin':
                            navigate_to("company_dashboard")
                        else:
                            navigate_to("dashboard")
                        return
                    elif result.get('show_registration'):
                        print(f"🔄 New OIDC user, showing registration form: {email}")
                        st.session_state.show_google_registration = True
                        st.session_state.verification_step = None
                        st.session_state.pending_registration = None
                        st.rerun()
                        return
            else:
                print("ℹ️ No email in st.user yet - waiting for OIDC callback")
    except Exception as e:
        print(f"ℹ️ OIDC check: {e}")
        pass
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

        .login-box h3,
            .stContainer h3,
            div[data-testid="stContainer"] h3 {
                color: #e0e0e0 !important;
                font-weight: 600 !important;
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

        /* ============================================================
        LABEL STYLING - Set to #c0c0c0
        ============================================================ */

        /* All Streamlit labels */
        .stTextInput label,
        .stSelectbox label,
        .stTextArea label,
        .stNumberInput label,
        .stDateInput label,
        .stTimeInput label,
        .stFileUploader label,
        .stMultiSelect label,
        .stColorPicker label {
            color: #c0c0c0 !important;
            font-weight: 500 !important;
        }

        /* Radio button labels */
        .stRadio label {
            color: #c0c0c0 !important;
        }

        /* Checkbox labels */
        .stCheckbox label {
            color: #c0c0c0 !important;
        }

        /* Form submit button label */
        .stFormSubmitButton label {
            color: #c0c0c0 !important;
        }

        /* Selectbox label */
        .stSelectbox label {
            color: #c0c0c0 !important;
        }

        /* Form styling - Input fields */
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

        .stTextInput > div > div > input::placeholder {
            color: #64748b !important;
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

        /* 2FA verification screen labels */
        .stTextInput label {
            color: #c0c0c0 !important;
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
        st.markdown("""
            <style>
            div[data-testid="stColumn"]:nth-child(1) .stContainer .stVerticalBlock {
                background: rgba(255, 255, 255, 0.03);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 2rem;
                border: 1px solid rgba(102, 126, 234, 0.1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
                    /* ============================================================
                RADIO BUTTON FIX - Make labels white
                ============================================================ */
                
                /* Target the radio button container */
                div[data-testid="stRadio"] {
                    color: #c0c0c0 !important;
                }
                
                /* Target all label elements inside radio */
                div[data-testid="stRadio"] label {
                    color: #c0c0c0 !important;
                }
                
                /* Target the span inside label (the text) */
                div[data-testid="stRadio"] label span {
                    color: #c0c0c0 !important;
                }
                
                /* Target the text directly */
                div[data-testid="stRadio"] label div {
                    color: wh#c0c0c0ite !important;
                }
                
                /* Target the p tag inside label */
                div[data-testid="stRadio"] label p {
                    color: #c0c0c0 !important;
                }
                
                /* When radio is selected */
                div[data-testid="stRadio"] label[data-checked="true"] span {
                    color: #667eea !important;
                }
                
                /* Hover state */
                div[data-testid="stRadio"] label:hover span {
                    color: #c0c0c0 !important;
                }
                    
            </style>
            """, unsafe_allow_html=True)
        with st.container():

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
                        # ✅ Get user by username or email
                        user = authenticate_user(username, password)
                        
                        if user:
                            # ✅ Get user's email from database
                            user_email = user.get('email')
                            role = user.get('role', 'viewer')
                            auth_provider = user.get('auth_provider', 'email_password')
                            
                            # ============================================================
                            # ✅ ADMIN BYPASS: System admins and admins skip 2FA
                            # ============================================================
                            if role in ['admin', 'system_admin']:
                                print(f"🔓 Admin user detected - bypassing 2FA: {username} (Role: {role})")
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
                                    return
                            
                            # ============================================================
                            # ✅ GOOGLE OAUTH USERS: No 2FA needed
                            # ============================================================
                            if auth_provider == 'google':
                                print(f"✅ Google OAuth user - no 2FA: {username}")
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
                                    return
                            
                            # ============================================================
                            # ✅ EMAIL/PASSWORD USERS: Check email verification + 2FA
                            # ============================================================
                            
                            # ✅ Check if email is verified (registration requirement)
                            if not user.get('email_verified', False):
                                st.warning("⚠️ Please verify your email address first. Check your inbox for the verification link.")
                                st.info("📧 If you didn't receive the email, please contact support.")
                                return
                            
                            # ✅ Login with 2FA - OTP will be sent to user's email from database
                            if auth_login_user(user, password, remember_me):
                                # Check if 2FA is required
                                if st.session_state.get('verification_step') == '2fa_otp':
                                    # ✅ OTP sent to user_email (from database)
                                    st.info(f"📧 A verification code has been sent to your registered email: {mask_email(user_email)}")
                                    st.rerun()
                                    return
                                else:
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
        with st.container():
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
    
    # ========== FINAL OIDC CHECK ==========
    if hasattr(st, 'user') and st.user:
        try:
            user_dict = dict(st.user) if st.user else {}
            email = user_dict.get('email')
            if email:
                print(f"🔄 OIDC user detected on login page: {email}")
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