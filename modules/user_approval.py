# modules/user_approval.py

import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def render_user_approval_page():
    """Admin page to approve pending user registrations"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👥 User Approval Management</h1>
        <p>Approve or reject pending user registrations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user has admin privileges
    user_role = st.session_state.get('user_role', '')
    if user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("You don't have permission to access this page.")
        return
    
    # Debug: Show count
    with st.expander("🔍 Debug Info", expanded=False):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_approved = 0")
        total_pending = cursor.fetchone()[0]
        st.write(f"Total pending users in database: {total_pending}")
        
        cursor.execute("SELECT id, username, email, full_name, role, is_approved FROM users WHERE is_approved = 0 LIMIT 5")
        pending_sample = cursor.fetchall()
        for p in pending_sample:
            st.write(f"  - ID: {p[0]}, Username: {p[1]}, Email: {p[2]}, Name: {p[3]}, Role: {p[4]}, Approved: {p[5]}")
        conn.close()
    
    # Get pending users
    if user_role in ['admin', 'system_admin']:
        pending_users = db.get_all_pending_users()
        st.markdown(f"### System-wide Pending Approvals ({len(pending_users)})")
    else:
        pending_users = db.get_pending_users(st.session_state.company_id)
        st.markdown(f"### Company Pending Approvals ({len(pending_users)})")
    
    if not pending_users:
        st.info("No pending user registrations.")
        return
    
    for user in pending_users:
        # Handle both dict and tuple formats
        if isinstance(user, dict):
            user_id = user.get('id')
            username = user.get('username', 'N/A')
            email = user.get('email', 'N/A')
            full_name = user.get('full_name', 'N/A')
            role = user.get('role', 'N/A')
            created_at = user.get('created_at', 'N/A')
            company_name = user.get('company_name', 'N/A')
        else:
            # Tuple format
            user_id = user[0] if len(user) > 0 else None
            username = user[1] if len(user) > 1 else 'N/A'
            email = user[2] if len(user) > 2 else 'N/A'
            full_name = user[3] if len(user) > 3 else 'N/A'
            role = user[5] if len(user) > 5 else 'N/A'
            created_at = user[6] if len(user) > 6 else 'N/A'
            company_name = user[8] if len(user) > 8 else 'N/A'
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{full_name}**")
                st.caption(f"@{username} | {email}")
            
            with col2:
                st.markdown(f"**Role:** {role}")
                st.markdown(f"**Company:** {company_name}")
                st.markdown(f"**Registered:** {str(created_at)[:16] if created_at else 'N/A'}")
            
            with col3:
                if st.button("✅ Approve", key=f"approve_{user_id}", use_container_width=True):
                    success = db.approve_user(user_id, st.session_state.user_id)
                    if success:
                        st.success(f"User {full_name} has been approved!")
                        st.rerun()
                    else:
                        st.error("Failed to approve user")
            
            with col4:
                if st.button("❌ Reject", key=f"reject_{user_id}", use_container_width=True):
                    success = db.reject_user(user_id, st.session_state.user_id)
                    if success:
                        st.warning(f"User {full_name} has been rejected.")
                        st.rerun()
                    else:
                        st.error("Failed to reject user")
            
            st.markdown("---")




def show_pending_approval_badge():
    """Show badge in sidebar for admin if there are pending approvals"""
    user_role = st.session_state.get('user_role', '')
    if user_role in ['admin', 'system_admin', 'company_admin']:
        if user_role in ['admin', 'system_admin']:
            pending_count = len(db.get_all_pending_users())
        else:
            pending_count = len(db.get_pending_users(st.session_state.company_id))
        
        if pending_count > 0:
            st.sidebar.markdown(f"🔔 **Pending Approvals: {pending_count}**")
            if st.sidebar.button("👥 View Pending Approvals", use_container_width=True):
                st.session_state.page = "user_approval"
                st.rerun()

