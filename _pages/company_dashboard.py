import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager
from modules.subscription import render_simple_subscription_status

db = UnifiedDatabaseManager()

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
    
    # Debug: Show current company_id
    st.info(f"🔍 Debug: Current Company ID = {company_id}")
    
    # Get company stats
    stats = db.get_company_stats(company_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Team Members", stats.get('total_users', 0))
    with col2:
        st.metric("📈 Total Analyses", stats.get('total_analyses', 0))
    with col3:
        st.metric("🏆 Won Tenders", stats.get('won_tenders', 0))
    with col4:
        st.metric("🎯 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
    
    # Direct query to verify
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check all analyses for this company
    cursor.execute("SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?", (company_id,))
    count = cursor.fetchone()[0]
    st.info(f"🔍 Database query: Found {count} analyses for company_id={company_id}")
    
    # Show the actual analyses
    cursor.execute("""
        SELECT id, tender_id, tender_title, recommended_bid, analysis_date
        FROM tender_analyses 
        WHERE company_id = ?
        ORDER BY analysis_date DESC
        LIMIT 5
    """, (company_id,))
    
    analyses = cursor.fetchall()
    conn.close()
    
    if analyses:
        st.markdown("### 📋 Recent Analyses in Database")
        for a in analyses:
            st.write(f"- ID: {a[0]}, Tender: {a[2][:50]}, Bid: {a[3]}, Date: {a[4]}")
    else:
        st.warning(f"No analyses found for company_id={company_id}")

def render_company_user_management(company_id):
    """Manage users within the company"""
    st.markdown("### 👥 Team Management")
    st.caption("Add, edit, and manage team members for your company")
    
    # Get current company users
    users, total = db.get_all_users_filtered(
        company_id=company_id,
        limit=50,
        offset=0
    )
    
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
                        password = db.generate_random_password()
                    
                    user_data = {
                        'username': username,
                        'password': password,
                        'email': email,
                        'full_name': full_name,
                        'phone': phone,
                        'role': role
                    }
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
    st.markdown(f"**Team Members ({total})**")
    
    if users:
        for user in users:
            # Skip showing company admins from other companies
            if user.get('role') == 'company_admin' and user.get('id') != st.session_state.user_id:
                continue
                
            with st.expander(f"👤 {user['full_name']} ({user['username']}) - {user['role'].title()}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    new_full_name = st.text_input("Full Name", value=user['full_name'], key=f"name_{user['id']}")
                    new_email = st.text_input("Email", value=user['email'], key=f"email_{user['id']}")
                    new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"phone_{user['id']}")
                    new_role = st.selectbox(
                        "Role",
                        options=["manager", "analyst", "viewer"],
                        index=["manager", "analyst", "viewer"].index(user['role']) if user['role'] in ["manager", "analyst", "viewer"] else 2,
                        key=f"role_{user['id']}"
                    )
                    new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"active_{user['id']}")
                    
                    if st.button("💾 Save Changes", key=f"save_{user['id']}"):
                        updates = {}
                        if new_full_name != user['full_name']:
                            updates['full_name'] = new_full_name
                        if new_email != user['email']:
                            updates['email'] = new_email
                        if new_phone != user.get('phone'):
                            updates['phone'] = new_phone
                        if new_role != user['role']:
                            updates['role'] = new_role
                        if new_active != (user.get('is_active', 1) == 1):
                            updates['is_active'] = 1 if new_active else 0
                        
                        if updates:
                            if db.update_user(user['id'], updates):
                                st.success("User updated!")
                                st.rerun()
                
                with col2:
                    if st.button("🔑 Reset Password", key=f"reset_{user['id']}"):
                        success, new_pw = db.reset_user_password(user['id'])
                        if success:
                            st.success(f"New password: `{new_pw}`")
                    
                    if user['id'] != st.session_state.user_id:
                        if st.button("🗑️ Remove User", key=f"delete_{user['id']}", type="secondary"):
                            if db.delete_user(user['id']):
                                st.success("User removed")
                                st.rerun()
                    
                    st.caption(f"Created: {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}")
    else:
        st.info("No team members found")


def render_company_tenders(company_id):
    """Manage tenders specific to this company"""
    st.markdown("### 📋 Company Tenders")
    
    # Fetch company tenders
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tender_id, tender_title, procuring_entity, 
               official_estimate, submission_deadline, created_at
        FROM company_tenders
        WHERE company_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (company_id,))
    
    tenders = cursor.fetchall()
    conn.close()
    
    if tenders:
        tender_data = []
        for t in tenders:
            tender_data.append({
                'ID': t[0],
                'Tender ID': t[1],
                'Title': t[2][:50],
                'Entity': t[3][:30],
                'Estimate': f"BDT {t[4]:,.0f}" if t[4] else 'N/A',
                'Deadline': t[5][:10] if t[5] else 'N/A',
                'Created': t[6][:10] if t[6] else 'N/A'
            })
        
        st.dataframe(pd.DataFrame(tender_data), use_container_width=True, hide_index=True)
        
        # View analyses for a specific tender
        st.markdown("#### View Tender Analyses")
        tender_options = {f"{t[1]} - {t[2][:50]}": t[0] for t in tenders}
        selected = st.selectbox("Select Tender", list(tender_options.keys()) if tender_options else [])
        
        if selected:
            tender_id = tender_options[selected]
            analyses = db.get_tender_analyses_by_company(company_id, tender_id)
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
    
    # Get winning statistics
    stats = db.get_winning_statistics(company_id)
    
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tenders", stats.get('total_tenders', 0))
        with col2:
            st.metric("Win Rate", f"{stats.get('our_win_rate', 0):.1f}%")
        with col3:
            st.metric("Competitor Wins", stats.get('competitor_wins', 0))
        
        # Bid performance
        st.markdown("### Bid Performance")
        if stats.get('avg_our_winning_price'):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Winning Bid", f"BDT {stats.get('avg_our_winning_price', 0):,.0f}")
            with col2:
                st.metric("Avg Competitor Winning", f"BDT {stats.get('avg_competitor_winning_price', 0):,.0f}")
    else:
        st.info("Not enough data for analytics. Complete more analyses to see insights.")