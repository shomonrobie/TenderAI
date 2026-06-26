import streamlit as st
from config import DEBUG_MODE, debug_print
from utils.helpers import (
    render_page_header, navigate_to, validate_password_strength
)
from utils.otp_service import OTPService
from database.unified_db_manager import db
import re
import logging

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
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def render_individual_registration():
    """Render individual registration form"""
    
    st.markdown("### 👤 Register as an Individual")
    st.caption("For freelancers, consultants, and sole proprietors (auto‑approved)")
    
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
            errors = validate_individual_registration(
                full_name, username, email, mobile, password, confirm_password, terms
            )
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # Store pending registration
                st.session_state.pending_registration = {
                    'account_type': 'individual',
                    'full_name': full_name.strip(),
                    'username': username.strip(),
                    'email': email.strip(),
                    'mobile': normalize_mobile(mobile),
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
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def render_otp_verification():
    """Render OTP verification screen"""
    
    st.subheader("🔐 Verify Your Email Address")
    
    email = st.session_state.get('verification_contact', '')
    masked_email = mask_email(email)
    
    st.info(f"A verification code has been sent to **{masked_email}**")
    st.caption("Please enter the 6-digit code to complete your registration")
    
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


def complete_registration():
    """Complete registration after OTP verification"""
    
    pending = st.session_state.get('pending_registration', {})
    
    if not pending:
        st.error("Registration data not found. Please restart.")
        return
    
    try:
        if pending['account_type'] == 'company':
            result = complete_company_registration(pending)
        else:
            result = complete_individual_registration(pending)
        
        if result['success']:
            st.success(result['message'])
            
            # Clear registration data
            st.session_state.verification_step = None
            st.session_state.verification_contact = None
            st.session_state.verification_purpose = None
            st.session_state.pending_registration = None
            
            # Show login button
            if st.button("🔐 Go to Login", use_container_width=True):
                navigate_to("login")
                st.rerun()
        else:
            st.error(result['message'])
            
    except Exception as e:
        logger.error(f"Registration completion error: {e}")
        st.error(f"Registration failed: {str(e)}")


def complete_company_registration(pending: dict) -> dict:
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


def complete_individual_registration(pending: dict) -> dict:
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
