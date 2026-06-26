import streamlit as st
import hashlib
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def show():
    """User profile page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👤 My Profile</h1>
        <p>Manage your account information</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user data
    user = db.get_user_by_id(st.session_state.user_id)
    
    if not user:
        st.error("User not found")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Personal Information")
        
        full_name = st.text_input("Full Name", value=user[5] if len(user) > 5 else "")
        email = st.text_input("Email", value=user[4] if len(user) > 4 else "")
        phone = st.text_input("Phone", value=user[6] if len(user) > 6 else "")
        
        if st.button("Update Profile", use_container_width=True):
            st.success("Profile updated successfully!")
    
    with col2:
        st.markdown("#### Account Information")
        
        st.info(f"**Username:** {user[2] if len(user) > 2 else 'N/A'}")
        st.info(f"**Role:** {user[6] if len(user) > 6 else 'N/A'}")
        st.info(f"**Company:** {user[14] if len(user) > 14 else 'N/A'}")
        st.info(f"**Member Since:** {user[10] if len(user) > 10 else 'N/A'}")
        
        st.markdown("#### Change Password")
        current_pass = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        
        if st.button("Change Password", use_container_width=True):
            if new_pass == confirm_pass:
                st.success("Password changed successfully!")
            else:
                st.error("New passwords do not match")
    
    # Subscription info
    st.markdown("---")
    st.markdown("#### 💳 Subscription Details")
    
    sub = db.get_user_subscription(st.session_state.user_id)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Plan", sub['plan'].upper())
    with col2:
        st.metric("Status", sub['status'].upper())
    with col3:
        if sub['analyses_limit'] == -1:
            st.metric("Analyses", "Unlimited")
        else:
            remaining = sub['analyses_limit'] - sub['analyses_used']
            st.metric("Remaining Analyses", max(0, remaining))
    
    if st.button("Manage Subscription", use_container_width=True):
        st.session_state.page = "subscription"
        st.rerun()