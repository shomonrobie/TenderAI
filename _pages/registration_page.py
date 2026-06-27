import streamlit as st
from config import DEBUG_MODE, debug_print
from utils.helpers import (
    render_page_header, navigate_to, validate_password_strength
)
from utils.otp_service import OTPService
from database.unified_db_manager import db
import re
import logging
from config.settings import Config  # ← Add this import

logger = logging.getLogger(__name__)


def show():
    """Complete Registration Page with Email OTP Verification"""
    debug_print("📝 Rendering registration page")
    
    # Check if in OTP verification step
    if st.session_state.get('verification_step') == 'email_otp':
        render_otp_verification()
        return
    
    # Page header
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>📝 Create New Account</h1>
            <p style="color: #555;">Choose the account type that fits you best</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Account type tabs
    tab1, tab2 = st.tabs(["🏢 **Company Registration**", "👤 **Individual Registration**"])
    
    with tab1:
        render_company_registration()
    
    with tab2:
        render_individual_registration()
    
    # Sidebar guidelines
    with st.sidebar:
        st.markdown("### 📋 Registration Guidelines")
        st.markdown("""
        **🏢 Company Accounts**
        - Requires admin approval
        - Suitable for teams and organisations
        - Full platform access after approval
        
        **👤 Individual Accounts**
        - Faster activation (auto‑approved)
        - Ideal for freelancers & consultants
        - Email verification required
        """)
        st.info("💡 Already have an account?")
        if st.button("→ Login Instead", use_container_width=True):
            navigate_to("login")
    from modules.footer import render_footer
    render_footer()

def render_company_registration_bak():
    """Render company registration form"""
    
    st.markdown("### 🏢 Register as a Company")
    st.caption("For construction companies, contractors, and organisations (requires admin approval)")
    
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
                # Store pending registration
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
                
                # Send OTP for email verification
                otp_service = OTPService(db)
                success, message = otp_service.send_verification_otp(
                    contact_type='email',
                    contact_value=email,
                    target_type='user',
                    target_id=0,
                    purpose='verification'
                )
                
                if success:
                    st.session_state.verification_step = 'email_otp'
                    st.session_state.verification_contact = email
                    st.session_state.verification_purpose = 'registration'
                    st.success(f"✅ {message}")
                    st.session_state['temp_otp'] = email_otp  # You'll need to return the OTP
                    st.success(message)
                    st.info(f"📱 Development Mode: Your OTP is: {email_otp}")  # Show in UI

                    st.rerun()
                else:
                    st.error(f"❌ {message}")

def render_individual_registration():
    """Render individual registration form"""
    
    st.markdown("### 👤 Register as an Individual")
    st.caption("For freelancers, consultants, and sole proprietors (auto‑approved)")
    
    # ========== GOOGLE REGISTRATION BUTTON (OUTSIDE FORM) ==========
    st.markdown("""
    <div style="text-align: center;">
        <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.5rem;">
            Register with your Google account
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_google1, col_google2, col_google3 = st.columns([1, 2, 1])
    with col_google2:
        if st.button("🔄 Register with Google", type="primary", use_container_width=True, key="google_reg_btn"):
            from modules.google_auth import get_google_auth_url
            auth_url = get_google_auth_url(registration_mode=True)
            if auth_url:
                st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========== TRADITIONAL REGISTRATION FORM ==========
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
                
                # Send OTP for email verification FIRST
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
                        'is_google_user': False  # Flag to indicate not a Google user
                    }
                    
                    st.session_state.verification_step = 'email_otp'
                    st.session_state.verification_contact = email
                    st.session_state.verification_purpose = 'registration'
                    
                    # Store OTP in session state - using a dedicated key
                    st.session_state['temp_otp_code'] = otp_code
                    
                    # Force session state to persist
                    st.session_state['_otp_sent'] = True
                    
                    print(f"🔍 DEBUG: OTP stored in session_state: {st.session_state.temp_otp_code}")
                    print(f"🔍 DEBUG: Full session_state keys: {list(st.session_state.keys())}")
                    
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # ========== FOOTER ==========
    st.markdown("""
    <div class="login-footer-text">
        Already have an account? <a href="?page=login">Login here</a>
    </div>
    """, unsafe_allow_html=True)

                        


def render_otp_verification_bak():
    """Render OTP verification screen"""
    
    st.subheader("🔐 Verify Your Email Address")
    
    email = st.session_state.get('verification_contact', '')
    masked_email = mask_email(email)
    
    st.info(f"A verification code has been sent to **{masked_email}**")
    st.caption("Please enter the 6-digit code to complete your registration")
    
    otp = st.text_input("Enter OTP Code", type="password", max_chars=6, key="reg_otp_input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with col1:
            if st.button("✓ Verify & Complete Registration", type="primary", use_container_width=True):
                print("🔍 DEBUG: Verify button clicked")
                print(f"🔍 DEBUG: OTP entered: {otp}")
                print(f"🔍 DEBUG: OTP length: {len(otp) if otp else 0}")
                
                if otp and len(otp) == 6:
                    print("🔍 DEBUG: OTP validation passed, attempting verification...")
                    
                    try:
                        otp_service = OTPService(db)
                        print(f"🔍 DEBUG: OTPService initialized")
                        
                        success, message, data = otp_service.verify_otp(
                            contact_type='email',
                            contact_value=email,
                            otp_code=otp,
                            purpose='verification'
                        )
                        
                        print(f"🔍 DEBUG: verify_otp returned: success={success}, message={message}, data={data}")
                        
                        if success:
                            print("🔍 DEBUG: OTP verification successful!")
                            st.success("✅ Email verified!")
                            
                            # Clear temp OTP
                            if 'temp_otp_code' in st.session_state:
                                del st.session_state.temp_otp_code
                            if '_otp_sent' in st.session_state:
                                del st.session_state._otp_sent
                            
                            print("🔍 DEBUG: Calling complete_registration()...")
                            complete_registration()
                            print("🔍 DEBUG: complete_registration() finished")
                            
                            st.rerun()
                        else:
                            print(f"🔍 DEBUG: OTP verification failed: {message}")
                            st.error(f"❌ {message}")
                            
                    except Exception as e:
                        print(f"🔍 DEBUG: EXCEPTION in verification: {e}")
                        import traceback
                        traceback.print_exc()
                        st.error(f"❌ An error occurred: {str(e)}")
                else:
                    print(f"🔍 DEBUG: Invalid OTP length: {len(otp) if otp else 0}")
                    st.warning("Please enter the 6-digit OTP code")
    with col2:
        if st.button("⟳ Resend OTP", use_container_width=True):
            pending = st.session_state.get('pending_registration', {})
            email = pending.get('email')
            
            if email:
                otp_service = OTPService(db)
                success, message = otp_service.resend_otp(
                    contact_type='email',
                    contact_value=email,
                    target_type='user',
                    target_id=0,
                    purpose='verification'
                )
                
                if success:
                    st.success("✅ New OTP sent!")
                else:
                    st.error(f"❌ {message}")
    
    # Back button
    st.divider()
    if st.button("← Back to Registration", use_container_width=True):
        st.session_state.verification_step = None
        st.session_state.verification_contact = None
        st.session_state.verification_purpose = None
        st.session_state.pending_registration = None
        st.rerun()

def render_company_registration():
    """Render company registration form"""
    
    st.markdown("### 🏢 Register as a Company")
    st.caption("For construction companies, contractors, and organisations (requires admin approval)")
    
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
            print("🔍 DEBUG: Company registration form submitted")
            
            errors = validate_company_registration(
                company_name, company_email, company_mobile, division, district,
                full_name, username, admin_mobile, email, password, confirm_password, terms
            )
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                print(f"🔍 DEBUG: Company validation passed for email: {email}")
                
                # Store pending registration
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
                
                print("🔍 DEBUG: Company pending registration stored in session state")
                
                # Send OTP for email verification
                otp_service = OTPService(db)
                success, message, otp_code = otp_service.send_verification_otp(
                    contact_type='email',
                    contact_value=email,
                    target_type='user',
                    target_id=0,
                    purpose='verification'
                )
                
                print(f"🔍 DEBUG: Company send_verification_otp returned: success={success}, message={message}, otp_code={otp_code}")
                
                if success:
                    st.session_state.verification_step = 'email_otp'
                    st.session_state.verification_contact = email
                    st.session_state.verification_purpose = 'registration'
                    
                    # Store OTP in session state
                    st.session_state.temp_otp_code = otp_code
                    
                    print(f"🔍 DEBUG: Company OTP stored in session_state: {st.session_state.temp_otp_code}")
                    
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
        
        # Auto-complete registration
        if st.button("✅ Complete Registration", type="primary", use_container_width=True):
            complete_registration()
            st.rerun()
        return
    
    st.info(f"A verification code has been sent to **{masked_email}**")
    st.caption("Please enter the 6-digit code to complete your registration")
    
    # Get OTP from session state or database
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


def render_otp_verification_bak2():
    """Render OTP verification screen"""
    
    st.subheader("🔐 Verify Your Email Address")
    
    email = st.session_state.get('verification_contact', '')
    masked_email = mask_email(email)
    
    st.info(f"A verification code has been sent to **{masked_email}**")
    st.caption("Please enter the 6-digit code to complete your registration")
    
    # --- DISPLAY OTP IN UI FOR DEVELOPMENT ---
    # Check if we're in development mode and have a temp OTP
    if hasattr(Config, 'DEBUG_OTP_PRINT') and Config.DEBUG_OTP_PRINT:
        temp_otp = st.session_state.get('temp_otp_code', '')
        if temp_otp:
            # Display OTP prominently in the UI
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
                    # Clear temp OTP
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
                    # Update the temp OTP in session state
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
        # Check if this is a Google user
        is_google_user = pending.get('is_google_user', False)
        
        if is_google_user:
            print("🔍 DEBUG: Google user registration")
            # For Google users, we might have different registration logic
            # Skip OTP verification since Google already verified the email
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
        logger.error(f"Registration completion error: {e}")
        st.error(f"Registration failed: {str(e)}")

def complete_registration_bak():
    """Complete registration after OTP verification"""
    
    pending = st.session_state.get('pending_registration', {})
    print(f"🔍 DEBUG: complete_registration started")
    print(f"🔍 DEBUG: pending_registration data: {pending}")
    
    if not pending:
        print("🔍 DEBUG: No pending registration found!")
        st.error("Registration data not found. Please restart.")
        return
    
    try:
        print(f"🔍 DEBUG: Account type: {pending.get('account_type')}")
        
        if pending['account_type'] == 'company':
            print("🔍 DEBUG: Calling complete_company_registration...")
            result = complete_company_registration(pending)
        else:
            print("🔍 DEBUG: Calling complete_individual_registration...")
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
            
            # Show success message and login option
            st.success(f"✅ {result['message']}")
            st.balloons()  # Optional: celebrate successful registration
            
            # Redirect to login after a short delay
            st.info("Redirecting to login page...")
            
            # Use session state to trigger navigation
            st.session_state._redirect_to_login = True
            st.rerun()
            
        else:
            print(f"🔍 DEBUG: Registration failed: {result.get('message')}")
            st.error(f"❌ {result.get('message', 'Registration failed')}")
            
    except Exception as e:
        print(f"🔍 DEBUG: EXCEPTION in complete_registration: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Registration completion error: {e}")
        st.error(f"Registration failed: {str(e)}")

def complete_company_registration(pending):
    """Complete company registration"""
    
    print("🔍 DEBUG: complete_company_registration called")
    print(f"🔍 DEBUG: pending data: {pending}")
    
    try:
        # First, create the company
        company_data = {
            'name': pending['company_name'],
            'email': pending['company_email'],
            'mobile': pending['company_mobile'],
            'division': pending.get('division', ''),
            'district': pending.get('district', ''),
            'status': 'pending'  # Company requires admin approval
        }
        
        print(f"🔍 DEBUG: Creating company with data: {company_data}")
        
        # Create company (this would need a create_company method)
        # For now, assuming you have a method to create company
        company_id = db.create_company(company_data)  # You might need to implement this
        
        print(f"🔍 DEBUG: Company created with ID: {company_id}")
        
        # Then create the admin user for this company
        user_data = {
            'username': pending['username'],
            'password': pending['password'],
            'email': pending['email'],
            'full_name': pending['full_name'],
            'phone': pending.get('phone', ''),
            'mobile_number': pending['admin_mobile'],
            'role': 'company_admin'
        }
        
        print(f"🔍 DEBUG: Calling create_user with user_data: {user_data}")
        
        success, result = db.create_user(
            company_id=company_id,
            user_data=user_data,
            created_by=None
        )
        
        print(f"🔍 DEBUG: create_user returned: success={success}, result={result}")
        
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
    
def complete_company_registration_bak6(pending: dict) -> dict:
    """Complete company registration"""
    
    # Check if company mobile exists
    existing_company = db.get_company_by_mobile(pending['company_mobile'])
    if existing_company:
        return {'success': False, 'message': 'Company mobile number already registered'}
    
    # Check if email exists
    existing_user = db.get_user_by_email(pending['email'])
    if existing_user:
        return {'success': False, 'message': 'Email already registered'}
    
    # Create company
    company_id = db.create_company(
        company_name=pending['company_name'],
        mobile_number=pending['company_mobile'],
        email=pending['company_email'],
        address=f"{pending['district']}, {pending['division']}"
    )
    
    if not company_id:
        return {'success': False, 'message': 'Company registration failed'}
    
    # Create admin user (requires approval)
    user_id = db.create_user(
        username=pending['username'],
        email=pending['email'],
        mobile_number=pending['admin_mobile'],
        password=pending['password'],
        full_name=pending['full_name'],
        role='company_admin',
        company_id=company_id
    )
    
    if user_id:
        # Mark email as verified
        db.update_user_verification(user_id, 'email', True)
        
        return {
            'success': True,
            'message': """
            🎉 **Company Registration Submitted Successfully!**
            
            Your account is pending admin approval. You will receive an email once approved.
            """.strip()
        }
    
    return {'success': False, 'message': 'User creation failed'}

def complete_individual_registration(pending):
    """Complete individual registration"""
    
    print("🔍 DEBUG: complete_individual_registration called")
    print(f"🔍 DEBUG: pending data: {pending}")
    
    try:
        # Prepare user data for create_user
        user_data = {
            'username': pending['username'],
            'password': pending['password'],  # Will be hashed by create_user
            'email': pending['email'],
            'full_name': pending['full_name'],
            'phone': pending.get('phone', ''),  # Optional phone field
            'mobile_number': pending['mobile'],  # This is the mobile number
            'role': 'individual'  # Set role for individual users
        }
        
        print(f"🔍 DEBUG: Calling create_user with user_data: {user_data}")
        
        # Create user (company_id = None for individual users, created_by = None)
        success, result = db.create_user(
            company_id=None,  # Individual users don't belong to a company
            user_data=user_data,
            created_by=None
        )
        
        print(f"🔍 DEBUG: create_user returned: success={success}, result={result}")
        
        if success:
            user_id = result  # result is the user_id when success is True
            print(f"🔍 DEBUG: User created with ID: {user_id}")
            
            return {
                'success': True,
                'message': f"Welcome {pending['full_name']}! Your account has been created.",
                'user_id': user_id
            }
        else:
            # result is the error message
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
    
def complete_individual_registration_bak5(pending: dict) -> dict:
    """Complete individual registration"""
    
    # Check if mobile exists
    existing_user = db.get_user_by_mobile(pending['mobile'])
    if existing_user:
        return {'success': False, 'message': 'Mobile number already registered'}
    
    # Check if email exists
    existing_user = db.get_user_by_email(pending['email'])
    if existing_user:
        return {'success': False, 'message': 'Email already registered'}
    
    # Create individual user (auto-approved)
    user_id = db.create_user(
        username=pending['username'],
        email=pending['email'],
        mobile_number=pending['mobile'],
        password=pending['password'],
        full_name=pending['full_name'],
        role='individual',
        company_id=None
    )
    
    if user_id:
        # Mark email as verified
        db.update_user_verification(user_id, 'email', True)
        
        return {
            'success': True,
            'message': """
            🎉 **Individual Account Created Successfully!**
            
            You can now login with your email and password.
            """.strip()
        }
    
    return {'success': False, 'message': 'Registration failed. Username may already exist.'}


def validate_company_registration(company_name, company_email, company_mobile, division, district,
                                  full_name, username, admin_mobile, email, password, confirm_password, terms):
    """Validate company registration input"""
    errors = []
    
    # Company validation
    if not company_name:
        errors.append("Company name is required")
    if not company_email:
        errors.append("Company email is required")
    if not company_mobile:
        errors.append("Company mobile number is required")
    elif not validate_bangladesh_mobile(company_mobile):
        errors.append("Invalid company mobile number (Format: 01XXXXXXXXX)")
    if not division:
        errors.append("Division is required")
    if not district:
        errors.append("District is required")
    
    # Admin validation
    if not full_name:
        errors.append("Admin full name is required")
    if not username:
        errors.append("Username is required")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters")
    if not admin_mobile:
        errors.append("Admin mobile number is required")
    elif not validate_bangladesh_mobile(admin_mobile):
        errors.append("Invalid admin mobile number (Format: 01XXXXXXXXX)")
    if not email:
        errors.append("Admin email is required")
    elif '@' not in email:
        errors.append("Invalid email address")
    if not password:
        errors.append("Password is required")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters")
    if password != confirm_password:
        errors.append("Passwords do not match")
    if not terms:
        errors.append("You must accept the Terms of Service")
    
    return errors


def validate_individual_registration(full_name, username, email, mobile, password, confirm_password, terms):
    """Validate individual registration input"""
    errors = []
    
    if not full_name:
        errors.append("Full name is required")
    if not username:
        errors.append("Username is required")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters")
    if not email:
        errors.append("Email is required")
    elif '@' not in email:
        errors.append("Invalid email address")
    if not mobile:
        errors.append("Mobile number is required")
    elif not validate_bangladesh_mobile(mobile):
        errors.append("Invalid mobile number (Format: 01XXXXXXXXX)")
    if not password:
        errors.append("Password is required")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters")
    if password != confirm_password:
        errors.append("Passwords do not match")
    if not terms:
        errors.append("You must accept the Terms of Service")
    
    return errors


def validate_bangladesh_mobile(mobile: str) -> bool:
    """Validate Bangladeshi mobile number"""
    if not mobile:
        return False
    mobile = re.sub(r'[\s\-+]', '', mobile)
    if mobile.startswith('88'):
        mobile = mobile[2:]
    pattern = r'^01[3-9]\d{8}$'
    return bool(re.match(pattern, mobile))


def normalize_mobile(mobile: str) -> str:
    """Normalize mobile number"""
    if not mobile:
        return mobile
    mobile = re.sub(r'[\s\-+]', '', mobile)
    if mobile.startswith('+88'):
        mobile = mobile[3:]
    elif mobile.startswith('88'):
        mobile = mobile[2:]
    return mobile


def mask_email(email: str) -> str:
    """Mask email for display"""
    if not email:
        return email
    parts = email.split('@')
    if len(parts) == 2:
        local, domain = parts
        if len(local) > 2:
            local = local[:2] + '*' * (len(local) - 2)
        return f"{local}@{domain}"
    return email

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
        
        # Generate a random password
        import secrets
        temp_password = secrets.token_urlsafe(16)
        
        # Prepare user data for create_google_user
        user_data = {
            'username': pending['username'],
            'email': pending['email'],
            'full_name': pending['full_name'],
            'phone': pending.get('phone', ''),
            'mobile_number': pending.get('mobile', ''),  # Optional for Google users
            'google_id': pending.get('google_id'),
        }
        
        print(f"🔍 DEBUG: Creating Google user with data: {user_data}")
        
        # Create user using the new create_google_user method
        success, user_id = db.create_google_user(user_data)
        
        if success:
            print(f"🔍 DEBUG: Google user created with ID: {user_id}")
            
            # Store additional profile info if needed
            if pending.get('specialization'):
                db.execute("""
                    UPDATE users SET specialization = ? WHERE id = ?
                """, (pending['specialization'], user_id))
            
            if pending.get('years_experience'):
                db.execute("""
                    UPDATE users SET years_experience = ? WHERE id = ?
                """, (pending['years_experience'], user_id))
            
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
    