"""
Individual User Registration (Email + Google Sign-In)
No company registration - for independent consultants/freelancers
"""

import streamlit as st
from modules.email_verification import send_verification_email, verify_otp
from database.unified_db_manager import UnifiedDatabaseManager
import re
import secrets
import bcrypt
from modules.google_auth import render_google_login_button, handle_google_callback

db = UnifiedDatabaseManager()

def debug_print(*args, **kwargs):
    """Debug print function"""
    from config import DEBUG_MODE
    if DEBUG_MODE:
        print(*args, **kwargs)

def render_individual_registration():
    """Registration page for individual users (Email + Google Sign-In)"""
    
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Individual Registration</h1>
        <p>For independent consultants, freelancers, and individual experts</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Google Sign-In option
    
    
    # Handle Google OAuth callback
    handle_google_callback()
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form()
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Sign up with Google")
        render_google_login_button()
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #666;'>OR</p>", unsafe_allow_html=True)
        
        # Manual registration form
        st.markdown("### Register with Email")
        
        with st.form("individual_registration_form"):
            full_name = st.text_input("Full Name *")
            email = st.text_input("Email Address *")
            phone = st.text_input("Phone Number")
            username = st.text_input("Username *", help="This will be your login username")
            password = st.text_input("Password *", type="password", help="Minimum 8 characters")
            confirm_password = st.text_input("Confirm Password *", type="password")
            
            specialization = st.selectbox(
                "Specialization",
                ["Construction Consultant", "Bid Analyst", "Quantity Surveyor", 
                 "Project Manager", "Civil Engineer", "Architect", "Contractor", "Other"]
            )
            years_experience = st.slider("Years of Experience", 0, 40, 5)
            
            terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *")
            
            submitted = st.form_submit_button("Register", type="primary", use_container_width=True)
            
            if submitted:
                # Validation
                errors = []
                if not all([full_name, email, username, password]):
                    errors.append("Please fill all required fields marked with *")
                elif password != confirm_password:
                    errors.append("Passwords do not match")
                elif len(password) < 8:
                    errors.append("Password must be at least 8 characters")
                elif not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
                    errors.append("Please enter a valid email address")
                elif not terms:
                    errors.append("Please accept the terms to continue")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    # Check if email already exists
                    existing = db.get_user_by_email(email)
                    if existing:
                        st.error("Email already registered. Please login instead.")
                        if st.button("Go to Login"):
                            st.session_state.page = "individual_login"
                            st.rerun()
                    else:
                        # Send verification email
                        if send_verification_email(email, full_name, 'signup'):
                            st.session_state.pending_verification = {
                                'email': email,
                                'full_name': full_name,
                                'phone': phone,
                                'username': username,
                                'password': password,
                                'specialization': specialization,
                                'years_experience': years_experience
                            }
                            st.session_state.show_otp_verification = True
                            st.success("Verification code sent to your email!")
                            st.rerun()
                        else:
                            st.error("Failed to send verification email. Please try again.")
    
    # OTP Verification
    if st.session_state.get('show_otp_verification'):
        st.markdown("---")
        st.markdown("### Verify Your Email")
        
        user_data = st.session_state.pending_verification
        
        with st.form("otp_verification_form"):
            otp = st.text_input("Enter 6-digit verification code", max_chars=6, type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Verify", type="primary", use_container_width=True):
                    success, message = verify_otp(user_data['email'], otp)
                    
                    if success:
                        # Create individual user account
                        hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        # Create a personal company (individual consultant)
                        company_data = {
                            'company_name': f"{user_data['full_name']} - Individual Consultant",
                            'email': user_data['email'],
                            'phone': user_data['phone'],
                            'division': user_data['specialization'],
                            'is_individual': True
                        }
                        
                        success, result = db.create_company(company_data)
                        
                        if success:
                            company_id = result
                            
                            # Create user
                            user_data_db = {
                                'username': user_data['username'],
                                'password': hashed_password,
                                'email': user_data['email'],
                                'full_name': user_data['full_name'],
                                'phone': user_data['phone'],
                                'role': 'individual',
                                'account_type': 'individual',
                                'specialization': user_data['specialization'],
                                'years_experience': user_data['years_experience'],
                                'is_approved': True,  # Auto-approve individuals
                                'auth_provider': 'email'
                            }
                            
                            user_success, user_result = db.create_user(company_id, user_data_db, 'individual')
                            
                            if user_success:
                                st.balloons()
                                st.success("Registration successful! You can now login.")
                                
                                # Clear session
                                st.session_state.show_otp_verification = False
                                st.session_state.pending_verification = None
                                
                                # Redirect to login
                                if st.button("Go to Login", use_container_width=True):
                                    st.session_state.page = "individual_login"
                                    st.rerun()
                            else:
                                st.error(f"Failed to create user: {user_result}")
                        else:
                            st.error(f"Failed to create account: {result}")
                    else:
                        st.error(message)
            
            with col2:
                if st.form_submit_button("Resend Code", use_container_width=True):
                    if send_verification_email(user_data['email'], user_data['full_name'], 'signup'):
                        st.success("New verification code sent!")
                    else:
                        st.error("Failed to resend code. Please try again.")


def render_individual_login():
    """Login page for individual users with Email + Google Sign-In"""
    
    from modules.google_auth import render_google_login_button, handle_google_callback
    from modules.email_verification import send_verification_email, verify_otp
    
    # Handle Google OAuth callback
    handle_google_callback(db)
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Individual Login</h1>
        <p>For consultants, freelancers, and individual experts</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Google Sign-In
        st.markdown("### Sign in with Google")
        render_google_login_button()
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #666;'>OR</p>", unsafe_allow_html=True)
        
        # Email login
        st.markdown("### Sign in with Email")
        
        with st.form("individual_login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            with col2:
                forgot = st.form_submit_button("Forgot Password?", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    # Authenticate individual user
                    user = db.get_user_by_email(email)
                    
                    if user and user.get('account_type') == 'individual' and user.get('auth_provider') == 'email':
                        if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                            # Send OTP for 2FA
                            if send_verification_email(email, user['full_name'], 'login'):
                                st.session_state.pending_2fa = {
                                    'user': user,
                                    'email': email
                                }
                                st.session_state.show_2fa = True
                                st.success("Verification code sent to your email!")
                                st.rerun()
                            else:
                                st.error("Failed to send verification code")
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("No individual account found with this email. Please register first.")
            
            if forgot:
                st.session_state.forgot_password_email = email
                st.session_state.show_forgot_password = True
                st.rerun()
        
        # New user registration
        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Don't have an account?</p>", unsafe_allow_html=True)
        
        if st.button("Register as Individual", use_container_width=True):
            st.session_state.page = "individual_register"
            st.rerun()
    
    # 2FA Verification
    if st.session_state.get('show_2fa'):
        st.markdown("---")
        st.markdown("### Enter Verification Code")
        
        with st.form("2fa_form"):
            otp = st.text_input("6-digit code sent to your email", max_chars=6, type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Verify", type="primary"):
                    success, message = verify_otp(st.session_state.pending_2fa['email'], otp)
                    
                    if success:
                        user = st.session_state.pending_2fa['user']
                        
                        # Set session state
                        st.session_state.logged_in = True
                        st.session_state.user_id = user['id']
                        st.session_state.username = user['username']
                        st.session_state.user_email = user['email']
                        st.session_state.full_name = user['full_name']
                        st.session_state.user_role = 'individual'
                        st.session_state.account_type = 'individual'
                        st.session_state.company_id = user['company_id']
                        
                        # Get company name
                        company = db.get_company_by_id(user['company_id'])
                        st.session_state.company_name = company.get('company_name', 'Individual Consultant') if company else 'Individual Consultant'
                        
                        # Get subscription
                        sub = db.get_effective_subscription(user['id'], user['company_id'])
                        st.session_state.subscription_plan = sub['plan']
                        st.session_state.analyses_used = sub['analyses_used']
                        st.session_state.analyses_limit = sub['analyses_limit']
                        
                        st.session_state.show_2fa = False
                        st.session_state.pending_2fa = None
                        
                        st.success(f"Welcome back, {user['full_name']}! 👋")
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error(message)
            
            with col2:
                if st.form_submit_button("Resend Code"):
                    if send_verification_email(
                        st.session_state.pending_2fa['email'], 
                        st.session_state.pending_2fa['user']['full_name'], 
                        'login'
                    ):
                        st.success("New code sent!")
                    else:
                        st.error("Failed to resend code")
    
    # Forgot Password
    if st.session_state.get('show_forgot_password'):
        st.markdown("---")
        st.markdown("### Reset Password")
        
        with st.form("forgot_password_form"):
            email = st.text_input("Email", value=st.session_state.get('forgot_password_email', ''))
            
            if st.form_submit_button("Send Reset Link", use_container_width=True):
                # Check if user exists
                user = db.get_user_by_email(email)
                if user and user.get('account_type') == 'individual':
                    # Generate reset token
                    reset_token = secrets.token_urlsafe(32)
                    
                    # Store in database (add this method to db_manager)
                    # db.store_password_reset_token(email, reset_token)
                    
                    # Send reset email (implement this)
                    # send_password_reset_email(email, reset_token)
                    
                    st.success("Password reset link sent to your email!")
                    st.session_state.show_forgot_password = False
                else:
                    st.error("No individual account found with this email")


def authenticate_individual_user(email, password):
    """Authenticate individual user"""
    user = db.get_user_by_email(email)
    
    if user and user.get('account_type') == 'individual' and user.get('auth_provider') == 'email':
        if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return user
    
    return None