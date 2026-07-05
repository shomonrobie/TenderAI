# _pages/company_dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import get_db_manager
from modules.subscription import render_simple_subscription_status


def show():
    """Company Admin Dashboard - Manage own company"""
    
    # Verify company admin access
    if st.session_state.user_role not in ['company_admin', 'admin']:
        st.error("🔒 Access denied. Company admin privileges required.")
        if st.button("→ Return to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        return
    
    company_id = st.session_state.company_id
    company_name = st.session_state.company_name
    
    st.markdown(f"""
    <div class="main-header">
        <h1>🏢 Company Dashboard</h1>
        <p>Manage {company_name} - Users, Tenders, and Analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different management functions
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "👥 Team Management", 
        "📋 Company Tenders",
        "📈 Company Analytics"
    ])
    
    with tab1:
        render_company_overview(company_id)
    
    with tab2:
        render_company_user_management(company_id)
    
    with tab3:
        render_company_tenders(company_id)
    
    with tab4:
        render_company_analytics(company_id)


def render_company_overview(company_id):
    """Render company statistics and overview"""
    st.markdown("### 📊 Company Overview")
    
    db = get_db_manager()
    
    # Get company stats using the CRUD method
    stats = db.get_company_stats(company_id)
    
    # Also get subscription info
    subscription = db.get_company_subscription(company_id)
    plan = subscription.get('subscription_tier', 'free') if subscription else 'free'
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("👥 Team Members", stats.get('total_users', 0))
    with col2:
        st.metric("📈 Total Analyses", stats.get('total_analyses', 0))
    with col3:
        st.metric("🏆 Total Bids", stats.get('total_bids', 0))
    with col4:
        st.metric("🎯 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
    with col5:
        st.metric("📋 Plan", plan.upper())
    
    # Show recent analyses
    st.markdown("### 📋 Recent Analyses")
    
    # Get recent analyses for this company
    analyses = db.query("""
        SELECT 
            id, tender_id, tender_title, recommended_bid, 
            confidence_score, analysis_date, bid_status
        FROM tender_analyses 
        WHERE company_id = ?
        ORDER BY analysis_date DESC
        LIMIT 5
    """, (company_id,))
    
    if analyses:
        df = pd.DataFrame(analyses)
        display_cols = ['tender_id', 'tender_title', 'recommended_bid', 'confidence_score', 'analysis_date', 'bid_status']
        display_df = df[[c for c in display_cols if c in df.columns]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No analyses found. Start analyzing tenders to see insights here.")


def render_company_user_management(company_id):
    """Manage users within the company"""
    st.markdown("### 👥 Team Management")
    st.caption("Add, edit, and manage team members for your company")
    
    db = get_db_manager()
    
    # Get current company users
    users = db.get_all_users(company_id=company_id)
    
    # Add new user
    with st.expander("➕ Add Team Member", expanded=False):
        with st.form("add_company_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
            with col2:
                role = st.selectbox("Role *", ["manager", "analyst", "viewer"])
                phone = st.text_input("Phone")
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            submitted = st.form_submit_button("Add Team Member", type="primary")
            if submitted:
                if not all([full_name, email, username]):
                    st.error("Please fill all required fields")
                elif not generate_password and password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    if generate_password:
                        import secrets
                        password = secrets.token_urlsafe(12)
                    
                    user_data = {
                        'username': username,
                        'password': password,
                        'email': email,
                        'full_name': full_name,
                        'phone': phone,
                        'role': role
                    }
                    
                    # Use the CRUD method
                    success, result = db.create_company_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        if generate_password:
                            st.success(f"✅ User {full_name} created! Password: `{password}`")
                        else:
                            st.success(f"✅ User {full_name} added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")
    
    # List and manage users
    total_users = len(users) if users else 0
    st.markdown(f"**Team Members ({total_users})**")
    
    if users:
        for user in users:
            # Skip showing company admins from other companies
            if user.get('role') == 'company_admin' and user.get('id') != st.session_state.user_id:
                continue
                
            with st.expander(f"👤 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'viewer').title()}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"name_{user.get('id')}")
                    new_email = st.text_input("Email", value=user.get('email', ''), key=f"email_{user.get('id')}")
                    new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"phone_{user.get('id')}")
                    new_role = st.selectbox(
                        "Role",
                        options=["manager", "analyst", "viewer"],
                        index=["manager", "analyst", "viewer"].index(user.get('role', 'viewer')) if user.get('role') in ["manager", "analyst", "viewer"] else 2,
                        key=f"role_{user.get('id')}"
                    )
                    new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"active_{user.get('id')}")
                    
                    if st.button("💾 Save Changes", key=f"save_{user.get('id')}"):
                        updates = {}
                        if new_full_name != user.get('full_name'):
                            updates['full_name'] = new_full_name
                        if new_email != user.get('email'):
                            updates['email'] = new_email
                        if new_phone != user.get('phone'):
                            updates['phone'] = new_phone
                        if new_role != user.get('role'):
                            updates['role'] = new_role
                        if new_active != (user.get('is_active', 1) == 1):
                            updates['is_active'] = 1 if new_active else 0
                        
                        if updates:
                            success = db.update_user(user.get('id'), updates)
                            if success:
                                st.success("User updated!")
                                st.rerun()
                
                with col2:
                    if st.button("🔑 Reset Password", key=f"reset_{user.get('id')}"):
                        success, new_pw = db.reset_user_password(user.get('id'))
                        if success:
                            st.success(f"New password: `{new_pw}`")
                    
                    if user.get('id') != st.session_state.user_id:
                        if st.button("🗑️ Remove User", key=f"delete_{user.get('id')}", type="secondary"):
                            if db.delete_user(user.get('id')):
                                st.success("User removed")
                                st.rerun()
                    
                    created_at = user.get('created_at', 'N/A')
                    if created_at and created_at != 'N/A':
                        st.caption(f"Created: {created_at[:10] if len(str(created_at)) > 10 else str(created_at)}")
    else:
        st.info("No team members found")


def render_company_tenders(company_id):
    """Manage tenders specific to this company"""
    st.markdown("### 📋 Company Tenders")
    
    db = get_db_manager()
    
    # Fetch company tenders using CRUD method
    tenders = db.get_company_tenders(company_id, limit=50)
    
    if tenders:
        tender_data = []
        for t in tenders:
            tender_data.append({
                'ID': t.get('id'),
                'Tender ID': t.get('tender_id'),
                'Title': str(t.get('tender_title', ''))[:50],
                'Entity': str(t.get('procuring_entity', ''))[:30],
                'Estimate': f"BDT {float(t.get('official_estimate', 0)):,.0f}" if t.get('official_estimate') else 'N/A',
                'Status': t.get('bid_status', 'draft'),
                'Deadline': t.get('submission_deadline', 'N/A')[:10] if t.get('submission_deadline') else 'N/A',
                'Created': t.get('created_at', 'N/A')[:10] if t.get('created_at') else 'N/A'
            })
        
        st.dataframe(pd.DataFrame(tender_data), use_container_width=True, hide_index=True)
        
        # View analyses for a specific tender
        st.markdown("#### View Tender Analyses")
        tender_options = {f"{t.get('tender_id')} - {t.get('tender_title', '')[:50]}": t.get('tender_id') for t in tenders}
        
        if tender_options:
            selected = st.selectbox("Select Tender", list(tender_options.keys()) if tender_options else [])
            
            if selected:
                tender_id = tender_options[selected]
                analyses = db.query("""
                    SELECT id, recommended_bid, confidence_score, 
                           analysis_date, bid_status
                    FROM tender_analyses 
                    WHERE company_id = ? AND tender_id = ?
                    ORDER BY analysis_date DESC
                    LIMIT 20
                """, (company_id, tender_id))
                
                if analyses:
                    st.dataframe(pd.DataFrame(analyses), use_container_width=True, hide_index=True)
                else:
                    st.info("No analyses found for this tender")
    else:
        st.info("No tenders created yet")
        if st.button("➕ Create New Tender", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()


def render_company_analytics(company_id):
    """Render analytics specific to this company"""
    st.markdown("### 📈 Company Analytics")
    
    db = get_db_manager()
    
    # Get analytics using the CRUD method
    stats = db.get_company_stats(company_id)
    
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Analyses", stats.get('total_analyses', 0))
        with col2:
            st.metric("🎯 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        with col3:
            st.metric("📋 Total Bids", stats.get('total_bids', 0))
        
        st.markdown("---")
        st.markdown("### 📈 Bid Performance")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🎯 Wins", stats.get('total_wins', 0))
        with col2:
            st.metric("📊 Avg Confidence", f"{stats.get('avg_confidence', 0):.1f}%")
        
        # Show monthly trend if data available
        monthly_data = db.query("""
            SELECT 
                strftime('%Y-%m', analysis_date) as month,
                COUNT(*) as count,
                AVG(confidence_score) as avg_conf,
                SUM(CASE WHEN bid_status = 'won' THEN 1 ELSE 0 END) as wins
            FROM tender_analyses
            WHERE company_id = ?
            GROUP BY strftime('%Y-%m', analysis_date)
            ORDER BY month DESC
            LIMIT 6
        """, (company_id,))
        
        if monthly_data:
            st.markdown("### 📊 Monthly Trend")
            df = pd.DataFrame(monthly_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Not enough data for monthly trends. Complete more analyses to see insights.")
    else:
        st.info("Not enough data for analytics. Complete more analyses to see insights.")