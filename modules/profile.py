# modules/profile.py

import streamlit as st
from database.unified_db_manager import db
from utils.otp_service import OTPService
from modules.registration import mask_contact


def render_profile():
    """User profile page with verification status"""
    
    st.title("👤 My Profile")
    
    if not st.session_state.get('logged_in'):
        st.warning("Please login to view your profile")
        return
    
    # Get user data
    user = db.get_user_by_id(st.session_state.user_id)
    if not user:
        st.error("User not found")
        return
    
    # Get company data if applicable
    company = None
    if st.session_state.get('company_id'):
        company = db.get_company_by_id(st.session_state.company_id)
    
    # Display profile
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Account Information")
        
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Full Name:** {user.get('full_name', 'N/A')}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Mobile:** {mask_contact(user.get('mobile_number', 'N/A'))}")
        st.write(f"**Role:** {user.get('role', 'user').title()}")
        
    with col2:
        st.subheader("✅ Verification Status")
        
        # Email verification
        email_verified = user.get('email_verified', False)
        if email_verified:
            st.success("📧 Email Verified ✓")
        else:
            st.warning("📧 Email Not Verified")
            if st.button("Verify Email", key="verify_email"):
                send_verification('email', user['email'], user['id'])
        
        # Mobile verification
        mobile_verified = user.get('mobile_verified', False)
        if mobile_verified:
            st.success("📱 Mobile Verified ✓")
        else:
            st.warning("📱 Mobile Not Verified")
            if st.button("Verify Mobile", key="verify_mobile"):
                send_verification('mobile', user['mobile_number'], user['id'])
    
    # Company info
    if company:
        st.divider()
        st.subheader("🏢 Company Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Company Name:** {company.get('company_name', 'N/A')}")
            st.write(f"**Email:** {company.get('email', 'N/A')}")
        with col2:
            st.write(f"**Mobile:** {mask_contact(company.get('mobile_number', 'N/A'))}")
            st.write(f"**Registration No:** {company.get('registration_no', 'N/A')}")


def send_verification(contact_type: str, contact_value: str, user_id: int):
    """Send verification OTP"""
    
    otp_service = OTPService(db)
    success, message = otp_service.send_verification_otp(
        contact_type=contact_type,
        contact_value=contact_value,
        target_type='user',
        target_id=user_id,
        purpose='verification'
    )
    
    if success:
        st.success(f"✅ {message}")
        st.session_state.verification_step = contact_type
        st.session_state.verification_contact = contact_value
    else:
        st.error(f"❌ {message}")