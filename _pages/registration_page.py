# _pages/registration_page.py - Remove manual handle_google_callback call

import streamlit as st
from utils.otp_service import OTPService
from utils.validators import (
    validate_individual_registration,
    validate_company_registration,
    validate_password_strength,
    normalize_mobile,
    validate_bangladesh_mobile
)
from utils.helpers import navigate_to
from modules.google_auth import render_google_login_button, get_oidc_component, process_oidc_user
from modules.footer import render_footer
import os

from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()



def show():
    """Main registration page with Google Sign-Up"""
    
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
    print("📄 REGISTRATION PAGE LOADED")
    print("=" * 60)
    print(f"🔍 logged_in: {st.session_state.get('logged_in', False)}")
    print(f"🔍 page: {st.session_state.get('page', 'None')}")
    
    # ========== CHECK IF USER IS ALREADY LOGGED IN ==========
    if st.session_state.get('logged_in', False):
        print("✅ User already logged in, redirecting to dashboard...")
        user_role = st.session_state.get('user_role', 'viewer')
        if user_role in ['admin', 'system_admin']:
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            navigate_to("company_dashboard")
        else:
            navigate_to("dashboard")
        return
    
    # ========== HANDLE OIDC AUTHENTICATION ==========
    # Check if user is authenticated via Streamlit's OIDC
    try:
        if hasattr(st, 'user') and st.user:
            # Try to get email from st.user
            try:
                user_dict = dict(st.user) if st.user else {}
                email = user_dict.get('email')
            except:
                email = None
            
            # If we have email, process the OIDC user
            if email:
                print(f"✅ OIDC user detected on registration page: {email}")
                
                # Process the OIDC user using the shared function
                result = process_oidc_user()
                
                if result:
                    if result.get('logged_in'):
                        print(f"✅ OIDC user logged in via registration page: {email}")
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
            else:
                print("ℹ️ No email in st.user yet - waiting for OIDC callback")
    except Exception as e:
        print(f"ℹ️ OIDC check on registration page: {e}")
        pass
    
    # ========== CHECK FOR OIDC CALLBACK (code in URL) ==========
    if 'code' in st.query_params:
        print("🔄 OIDC callback detected on registration page")
        # Let the process_oidc_user handle it
        if hasattr(st, 'user') and st.user:
            try:
                user_dict = dict(st.user) if st.user else {}
                email = user_dict.get('email')
                if email:
                    result = process_oidc_user()
                    if result and result.get('logged_in'):
                        user_role = st.session_state.get('user_role', 'viewer')
                        st.query_params.clear()
                        if user_role in ['admin', 'system_admin']:
                            navigate_to("admin_dashboard")
                        elif user_role == 'company_admin':
                            navigate_to("company_dashboard")
                        else:
                            navigate_to("dashboard")
                        return
            except Exception as e:
                print(f"⚠️ OIDC callback processing error: {e}")
    
    # Check if showing Google registration (from OIDC)
    if st.session_state.get('show_google_registration'):
        print("🔍 Showing Google registration form")
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    # Check if we're in OTP verification step
    if st.session_state.get('verification_step') == 'email_otp':
        print("🔍 Rendering OTP verification")
        render_otp_verification()
        return
    
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
        
        /* Main container */
        .register-main-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
        }
        
        .register-header {
            text-align: center;
            padding: 1rem 0 1.5rem 0;
        }
        
        .register-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }
        
        .register-header p {
            color: #94a3b8;
            font-size: 1.1rem;
        }
        
        /* ========== FIX: Radio Button Labels ========== */
        .stRadio > div {
            gap: 1rem !important;
        }
        
        .stRadio label {
            color: #e0e0e0 !important;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500 !important;
        }
        
        .stRadio label:hover {
            background: rgba(102, 126, 234, 0.15);
            border-color: rgba(102, 126, 234, 0.3);
        }
        
        .stRadio label span {
            color: #e0e0e0 !important;
        }
        
        .stRadio div[role="radiogroup"] label {
            color: #e0e0e0 !important;
        }
        
        /* ========== FIX: Checkbox Labels ========== */
        .stCheckbox label {
            color: #c0c0c0 !important;
            font-weight: 500 !important;
        }
        
        .stCheckbox label span {
            color: #c0c0c0 !important;
        }
        
        /* ========== FIX: All Labels ========== */
        .stTextInput label,
        .stSelectbox label,
        .stTextArea label {
            color: #c0c0c0 !important;
            font-weight: 500 !important;
        }
        
        /* ========== FIX: Form Container ========== */
        div[data-testid="stColumn"]:nth-child(1) .stContainer .stVerticalBlock {
            background: rgba(255, 255, 255, 0.03) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 16px !important;
            padding: 2rem !important;
            border: 1px solid rgba(102, 126, 234, 0.1) !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* ========== FIX: Branding Box ========== */
        div[data-testid="stColumn"]:nth-child(2) .stContainer .stVerticalBlock {
            background: linear-gradient(145deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05)) !important;
            border-radius: 16px !important;
            padding: 2rem !important;
            text-align: center !important;
            border: 1px solid rgba(102, 126, 234, 0.1) !important;
            height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
        }
        
        /* Branding text */
        .branding-box h3 {
            color: #e0e0e0 !important;
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            background: linear-gradient(135deg, #667eea, #764ba2) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
        }
        
        .branding-box p {
            color: #94a3b8 !important;
            font-size: 0.95rem !important;
            margin: 0.5rem 0 !important;
        }
        
        .branding-box .tagline {
            color: #64748b !important;
            font-size: 0.85rem !important;
        }
        
        /* ========== FIX: Feature List ========== */
        .feature-list li {
            color: #94a3b8 !important;
            font-size: 0.85rem !important;
            padding: 0.3rem 0 !important;
            list-style: none !important;
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
        }
        
        .feature-list li::before {
            content: '✓' !important;
            color: #667eea !important;
            font-weight: bold !important;
            font-size: 1rem !important;
        }
        
        /* ========== FIX: Form Inputs ========== */
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
        
        .stSelectbox > div > div > select {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #e0e0e0 !important;
            border-radius: 8px !important;
        }
        
        .stSelectbox > div > div > select option {
            background: #1a1a2e !important;
            color: #e0e0e0 !important;
        }
        
        /* ========== FIX: Buttons ========== */
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
        
        /* ========== FIX: Divider ========== */
        .or-divider {
            text-align: center;
            color: #94a3b8 !important;
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
        
        /* ========== FIX: Footer Text ========== */
        .register-footer-text {
            text-align: center;
            color: #94a3b8 !important;
            font-size: 0.75rem;
            margin-top: 0.5rem;
        }
        
        .register-footer-text a {
            color: #667eea !important;
            text-decoration: none;
        }
        
        .register-footer-text a:hover {
            text-decoration: underline;
        }
        
        /* ========== FIX: OTP Display ========== */
        .otp-display {
            background-color: rgba(255, 255, 255, 0.05) !important;
            padding: 20px !important;
            border-radius: 10px !important;
            text-align: center !important;
            border: 2px dashed #4CAF50 !important;
        }
        
        .otp-display h1 {
            color: #4CAF50 !important;
            font-size: 48px !important;
            letter-spacing: 10px !important;
            margin: 0 !important;
        }
        
        .otp-display p {
            color: #94a3b8 !important;
            margin: 10px 0 0 0 !important;
        }
        
        /* ========== RESPONSIVE ========== */
        @media (max-width: 768px) {
            .register-main-container {
                padding: 0.5rem 1rem;
            }
            .branding-box {
                margin-top: 1rem;
                padding: 1.5rem;
            }
            .register-box {
                padding: 1.5rem;
            }
            .register-header h1 {
                font-size: 2rem;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    # ========== MAIN CONTENT ==========
    st.markdown('<div class="register-main-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="register-header">
        <h1>🚀 Create Your TenderAI Account</h1>
        <p>Join Bangladesh's First AI-Powered Tender Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== TWO COLUMN LAYOUT ==========
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        with st.container():
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
            </style>
            """, unsafe_allow_html=True)
            
            # ========== ACCOUNT TYPE SELECTION ==========
            st.markdown("### 📝 Choose Account Type")
            
            account_type = st.radio(
                "Select Account Type",
                ["Individual", "Company"],
                horizontal=True,
                key="reg_account_type"
            )
            
            st.markdown("---")
            
            # ========== GOOGLE REGISTRATION BUTTON ==========
            st.markdown("""
            <div style="text-align: center;">
                <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.5rem;">
                    Register with your Google account
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Check if OIDC is configured by checking secrets (instead of get_oidc_component)
            try:
                if "auth" in st.secrets and "client_id" in st.secrets["auth"]:
                    render_google_login_button(registration_mode=True)
                else:
                    st.warning("⚠️ Google Sign-Up is not available. Please use the form below.")
            except:
                st.warning("⚠️ Google Sign-Up is not available. Please use the form below.")
            
            st.markdown('<div class="or-divider">OR</div>', unsafe_allow_html=True)
            
            # ========== TRADITIONAL REGISTRATION FORM ==========
            if account_type == "Individual":
                render_individual_registration()
            else:
                render_company_registration()
            
            st.markdown("""
            <div class="register-footer-text">
                Already have an account? <a href="?page=login">Login here</a>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown("""
            <style>
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
    
    # ========== FOOTER ==========
    st.markdown("---")
    render_footer()



def render_individual_registration():
    """Render individual registration form"""
    
    with st.form("individual_register_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name *", placeholder="John Doe")
            username = st.text_input("Username *", placeholder="johndoe")
            email = st.text_input("Email Address *", placeholder="john@example.com")
        with col2:
            mobile = st.text_input("Mobile Number *", placeholder="01XXXXXXXXX")
            password = st.text_input("Password *", type="password", placeholder="••••••••")
            confirm_password = st.text_input("Confirm Password *", type="password", placeholder="••••••••")
        
        # Password strength
        if password:
            score, message, color = validate_password_strength(password)
            st.progress(score / 100, text=f"Strength: {score}%")
        
        terms = st.checkbox("I agree to the **Terms of Service** and **Privacy Policy** *", key="ind_reg_terms")
        
        submitted = st.form_submit_button("📝 Register Individual Account", type="primary", use_container_width=True)
        
        if submitted:
            print("🔍 DEBUG: Registration form submitted")
            
            errors = validate_individual_registration(
                full_name, username, email, mobile, password, confirm_password, terms
            )
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                print(f"🔍 DEBUG: Validation passed for email: {email}")
                
                # Send OTP for email verification
                otp_service = OTPService(db)
                success, message, otp_code = otp_service.send_verification_otp(
                    contact_type='email',
                    contact_value=email,
                    target_type='user',
                    target_id=0,
                    purpose='verification'
                )
                
                print(f"🔍 DEBUG: send_verification_otp returned: success={success}, message={message}, otp_code={otp_code}")
                
                if success:
                    # Store ALL data in session state
                    st.session_state.pending_registration = {
                        'account_type': 'individual',
                        'full_name': full_name.strip(),
                        'username': username.strip(),
                        'email': email.strip(),
                        'mobile': normalize_mobile(mobile),
                        'password': password,
                        'is_google_user': False
                    }
                    
                    st.session_state.verification_step = 'email_otp'
                    st.session_state.verification_contact = email
                    st.session_state.verification_purpose = 'registration'
                    
                    # Store OTP in session state
                    st.session_state['temp_otp_code'] = otp_code
                    st.session_state['_otp_sent'] = True
                    
                    print(f"🔍 DEBUG: OTP stored in session_state: {st.session_state.temp_otp_code}")
                    
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def render_company_registration():
    """Render company registration form"""
    
    with st.form("company_register_form"):
        # Company Information
        st.markdown("#### 📌 Company Information")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name *", placeholder="e.g., ABC Construction Ltd.")
            company_email = st.text_input("Company Email *", placeholder="info@company.com")
            company_mobile = st.text_input("Company Mobile Number *", placeholder="01XXXXXXXXX")
        with col2:
            division = st.selectbox(
                "Division / Region *",
                ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
            )
            district = st.text_input("District *", placeholder="e.g., Dhaka")
        
        # Admin Account Details
        st.markdown("#### 👤 Admin Account Details")
        col3, col4 = st.columns(2)
        with col3:
            full_name = st.text_input("Full Name (Admin) *", placeholder="John Doe")
            username = st.text_input("Username *", placeholder="johndoe")
            admin_mobile = st.text_input("Admin Mobile Number *", placeholder="01XXXXXXXXX")
        with col4:
            email = st.text_input("Admin Email *", placeholder="john@company.com")
            password = st.text_input("Password *", type="password", placeholder="••••••••")
            confirm_password = st.text_input("Confirm Password *", type="password", placeholder="••••••••")
        
        # Password strength
        if password:
            score, message, color = validate_password_strength(password)
            st.progress(score / 100, text=f"Strength: {score}%")
        
        terms = st.checkbox("I agree to the **Terms of Service** and **Privacy Policy** *", key="comp_reg_terms")
        
        submitted = st.form_submit_button("🚀 Submit Company Registration", type="primary", use_container_width=True)
        
        if submitted:
            errors = validate_company_registration(
                company_name, company_email, company_mobile, division, district,
                full_name, username, admin_mobile, email, password, confirm_password, terms
            )
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # Send OTP for email verification
                otp_service = OTPService(db)
                success, message, otp_code = otp_service.send_verification_otp(
                    contact_type='email',
                    contact_value=email,
                    target_type='user',
                    target_id=0,
                    purpose='verification'
                )
                
                if success:
                    st.session_state.pending_registration = {
                        'account_type': 'company',
                        'company_name': company_name.strip(),
                        'company_email': company_email.strip(),
                        'company_mobile': normalize_mobile(company_mobile),
                        'division': division,
                        'district': district.strip(),
                        'full_name': full_name.strip(),
                        'username': username.strip(),
                        'admin_mobile': normalize_mobile(admin_mobile),
                        'email': email.strip(),
                        'password': password
                    }
                    
                    st.session_state.verification_step = 'email_otp'
                    st.session_state.verification_contact = email
                    st.session_state.verification_purpose = 'registration'
                    st.session_state['temp_otp_code'] = otp_code
                    st.session_state['_otp_sent'] = True
                    
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def render_otp_verification():
    """Render OTP verification screen"""
    
    st.subheader("🔐 Verify Your Email Address")
    
    email = st.session_state.get('verification_contact', '')
    masked_email = mask_email(email)
    purpose = st.session_state.get('verification_purpose', 'registration')
    
    # Check if this is a Google registration (no OTP needed)
    if purpose == 'google_registration':
        st.info("✅ Your Google account has been verified!")
        st.markdown("### 🎉 Completing your registration...")
        
        if st.button("✅ Complete Registration", type="primary", use_container_width=True):
            complete_registration()
            st.rerun()
        return
    
    st.info(f"A verification code has been sent to **{masked_email}**")
    st.caption("Please enter the 6-digit code to complete your registration")
    
    # Get OTP from session state
    temp_otp = st.session_state.get('temp_otp_code', '')
    
    # If not in session, try database
    if not temp_otp and email:
        try:
            otp_record = db.query_one("""
                SELECT otp_code FROM otp_verification
                WHERE contact_value = ? AND is_used = 0
                ORDER BY created_at DESC LIMIT 1
            """, (email,))
            if otp_record:
                temp_otp = otp_record['otp_code']
                st.session_state.temp_otp_code = temp_otp
        except Exception as e:
            print(f"Error fetching OTP: {e}")
    
    # Display OTP in development mode
    if temp_otp and temp_otp != 'GOOGLE_VERIFIED':
        st.markdown("---")
        st.markdown("### 📱 Development Mode - Your OTP Code")
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border: 2px dashed #4CAF50;">
            <h1 style="color: #4CAF50; font-size: 48px; letter-spacing: 10px; margin: 0;">{temp_otp}</h1>
            <p style="color: #666; margin: 10px 0 0 0;">Copy this code and paste it below</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.caption("⚠️ This code is only shown in development mode. In production, it will be sent via email.")
    
    otp = st.text_input("Enter OTP Code", type="password", max_chars=6, key="reg_otp_input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✓ Verify & Complete Registration", type="primary", use_container_width=True):
            if otp and len(otp) == 6:
                otp_service = OTPService(db)
                success, message, _ = otp_service.verify_otp(
                    contact_type='email',
                    contact_value=email,
                    otp_code=otp,
                    purpose='verification'
                )
                
                if success:
                    st.success("✅ Email verified!")
                    if 'temp_otp_code' in st.session_state:
                        del st.session_state.temp_otp_code
                    complete_registration()
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.warning("Please enter the 6-digit OTP code")
    
    with col2:
        if st.button("⟳ Resend OTP", use_container_width=True):
            pending = st.session_state.get('pending_registration', {})
            email = pending.get('email')
            
            if email:
                otp_service = OTPService(db)
                success, message, new_otp = otp_service.resend_otp(
                    contact_type='email',
                    contact_value=email,
                    target_type='user',
                    target_id=0,
                    purpose='verification'
                )
                
                if success:
                    st.session_state.temp_otp_code = new_otp
                    st.success("✅ New OTP sent!")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # Back button
    st.divider()
    if st.button("← Back to Registration", use_container_width=True):
        st.session_state.verification_step = None
        st.session_state.verification_contact = None
        st.session_state.verification_purpose = None
        st.session_state.pending_registration = None
        if 'temp_otp_code' in st.session_state:
            del st.session_state.temp_otp_code
        st.rerun()


def complete_registration():
    """Complete registration after OTP verification"""
    
    pending = st.session_state.get('pending_registration', {})
    print(f"🔍 DEBUG: complete_registration started")
    print(f"🔍 DEBUG: pending_registration data: {pending}")
    
    if not pending:
        print("🔍 DEBUG: No pending registration found!")
        st.error("Registration data not found. Please restart.")
        return
    
    try:
        is_google_user = pending.get('is_google_user', False)
        
        if is_google_user:
            print("🔍 DEBUG: Google user registration")
            result = complete_google_registration(pending)
        elif pending['account_type'] == 'company':
            print("🔍 DEBUG: Company registration")
            result = complete_company_registration(pending)
        else:
            print("🔍 DEBUG: Individual registration")
            result = complete_individual_registration(pending)
        
        print(f"🔍 DEBUG: Registration result: {result}")
        
        if result['success']:
            print("🔍 DEBUG: Registration successful!")
            
            # Clear registration data
            st.session_state.verification_step = None
            st.session_state.verification_contact = None
            st.session_state.verification_purpose = None
            st.session_state.pending_registration = None
            if 'temp_otp_code' in st.session_state:
                del st.session_state.temp_otp_code
            
            # Store success message and redirect to login
            st.session_state._registration_success = result['message']
            st.session_state._show_registration_success = True
            st.session_state.page = 'login'
            st.session_state.logged_in = False
            
            print("🔍 DEBUG: Redirecting to login page with success message")
            st.rerun()
            
        else:
            print(f"🔍 DEBUG: Registration failed: {result.get('message')}")
            st.error(f"❌ {result.get('message', 'Registration failed')}")
            
    except Exception as e:
        print(f"🔍 DEBUG: EXCEPTION in complete_registration: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Registration failed: {str(e)}")


def complete_individual_registration(pending):
    """Complete individual registration"""
    
    print("🔍 DEBUG: complete_individual_registration called")
    
    try:
        user_data = {
            'username': pending['username'],
            'password': pending['password'],
            'email': pending['email'],
            'full_name': pending['full_name'],
            'phone': pending.get('phone', ''),
            'mobile_number': pending['mobile'],
            'role': 'individual'
        }
        
        print(f"🔍 DEBUG: Creating user with data: {user_data}")
        
        success, result = db.create_user(
            company_id=None,
            user_data=user_data,
            created_by=None
        )
        
        if success:
            user_id = result
            print(f"🔍 DEBUG: User created with ID: {user_id}")
            
            return {
                'success': True,
                'message': f"Welcome {pending['full_name']}! Your account has been created.",
                'user_id': user_id
            }
        else:
            print(f"🔍 DEBUG: User creation failed: {result}")
            return {
                'success': False,
                'message': f"Registration failed: {result}"
            }
        
    except Exception as e:
        print(f"🔍 DEBUG: Error in complete_individual_registration: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"Registration failed: {str(e)}"
        }


def complete_company_registration(pending):
    """Complete company registration"""
    
    print("🔍 DEBUG: complete_company_registration called")
    
    try:
        # First create the company
        company_data = {
            'name': pending['company_name'],
            'email': pending['company_email'],
            'mobile': pending['company_mobile'],
            'division': pending.get('division', ''),
            'district': pending.get('district', ''),
            'status': 'pending'
        }
        
        # Create company
        company_id = db.create_company(company_data)
        
        if not company_id:
            return {
                'success': False,
                'message': "Failed to create company"
            }
        
        print(f"🔍 DEBUG: Company created with ID: {company_id}")
        
        # Create admin user
        user_data = {
            'username': pending['username'],
            'password': pending['password'],
            'email': pending['email'],
            'full_name': pending['full_name'],
            'phone': pending.get('phone', ''),
            'mobile_number': pending['admin_mobile'],
            'role': 'company_admin'
        }
        
        success, result = db.create_user(
            company_id=company_id,
            user_data=user_data,
            created_by=None
        )
        
        if success:
            user_id = result
            print(f"🔍 DEBUG: Admin user created with ID: {user_id}")
            
            return {
                'success': True,
                'message': f"Company {pending['company_name']} registered! Please wait for admin approval.",
                'user_id': user_id,
                'company_id': company_id
            }
        else:
            print(f"🔍 DEBUG: User creation failed: {result}")
            return {
                'success': False,
                'message': f"Registration failed: {result}"
            }
        
    except Exception as e:
        print(f"🔍 DEBUG: Error in complete_company_registration: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"Registration failed: {str(e)}"
        }


def complete_google_registration(pending):
    """Complete Google user registration"""
    
    print("🔍 DEBUG: complete_google_registration called")
    
    try:
        # Check if user already exists
        existing_user = db.get_user_by_email(pending['email'])
        if existing_user:
            print(f"🔍 DEBUG: User already exists: {existing_user['id']}")
            return {
                'success': True,
                'message': f"Welcome back, {pending['full_name']}!",
                'user_id': existing_user['id']
            }
        
        # Prepare user data for Google user
        user_data = {
            'username': pending['username'],
            'email': pending['email'],
            'full_name': pending['full_name'],
            'phone': pending.get('phone', ''),
            'mobile_number': pending.get('mobile', ''),  # Optional for Google users
            'google_id': pending.get('google_id'),
            'role': 'individual'
        }
        
        print(f"🔍 DEBUG: Creating Google user with data: {user_data}")
        
        # Create user using the create_google_user method
        success, user_id = db.create_google_user(user_data)
        
        if success:
            print(f"🔍 DEBUG: Google user created with ID: {user_id}")
            
            return {
                'success': True,
                'message': f"Welcome {pending['full_name']}! Your Google account has been linked.",
                'user_id': user_id
            }
        else:
            print(f"🔍 DEBUG: Google user creation failed: {user_id}")
            return {
                'success': False,
                'message': f"Registration failed: {user_id}"
            }
        
    except Exception as e:
        print(f"🔍 DEBUG: Error in complete_google_registration: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"Registration failed: {str(e)}"
        }


def mask_email(email: str) -> str:
    """Mask email for display"""
    if not email:
        return ""
    parts = email.split('@')
    if len(parts) != 2:
        return email
    username, domain = parts
    if len(username) <= 2:
        masked_username = username[0] + '*' * (len(username) - 1)
    else:
        masked_username = username[:2] + '*' * (len(username) - 2)
    return f"{masked_username}@{domain}"