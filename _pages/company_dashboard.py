"""
Company Dashboard Module - State-Driven View Router Pattern
For Company Admins to manage their own company
All database operations use CRUD methods - NO RAW SQL
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.validators import (
    validate_email,
    validate_username,
    validate_bangladesh_mobile,
    normalize_mobile
)
from utils.helpers import safe_compare, safe_strip
from database.unified_db_manager import get_db_manager
import json
from modules.company_user_management import render_company_user_management

def show():
    """Company Admin Dashboard - Manage own company"""
    
    # Verify company admin access
    if st.session_state.user_role not in ['company_admin', 'admin']:
        st.error("🔒 Access denied. Company admin privileges required.")
        if st.button("→ Return to Dashboard", key="comp_dash_return"):
            st.session_state.page = "dashboard"
            st.rerun()
        return
    
    # Initialize session state
    if "comp_view" not in st.session_state:
        st.session_state.comp_view = "overview"
    if "comp_selected_user_id" not in st.session_state:
        st.session_state.comp_selected_user_id = None
    if "comp_selected_tender_id" not in st.session_state:
        st.session_state.comp_selected_tender_id = None
    if "comp_selected_analysis_id" not in st.session_state:
        st.session_state.comp_selected_analysis_id = None
    
    # ✅ TRACK: Source for back navigation
    if "tender_detail_source" not in st.session_state:
        st.session_state.tender_detail_source = None
    
    # ✅ CHECK: If navigating to tender detail from company dashboard
    if st.session_state.get('page') == "tender_management" and st.session_state.get('view_tender_detail'):
        # Set source for back navigation
        st.session_state.tender_detail_source = "company_dashboard"
        
        # Render the tender detail page with custom back button
        render_tender_detail_with_company_back(st.session_state.view_tender_detail)
        return
    
    company_id = st.session_state.company_id
    company_name = st.session_state.company_name
    db = get_db_manager()
    st.markdown(f"""
    <div class="main-header">
        <h1>🏢 Company Dashboard</h1>
        <p>Manage {company_name} - Users, Tenders, and Analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different management functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "👥 Team Management", 
        "📋 All Tenders",
        "📈 Analytics",
        "🔐 Access Management"
    ])
    
    with tab1:
        if st.session_state.comp_view == "analysis_detail" and st.session_state.comp_selected_analysis_id:
            render_analysis_detail_view(db, company_id, st.session_state.comp_selected_analysis_id)
        else:
            render_company_overview(company_id)
    
    with tab2:
        render_team_management(company_id)
    
    with tab3:
        render_company_tenders(company_id)
    
    with tab4:
        render_company_analytics(company_id)
    with tab5:
        render_company_user_management(db, company_id)




def render_tender_detail_with_company_back(tender_data: Dict[str, Any]):
    """Render tender detail page with custom back button to company dashboard"""
    
    from modules.tender_management import _render_tender_detail_page
    
    # ✅ First, render the original tender detail page
    _render_tender_detail_page(tender_data)
    
    # ✅ Then, add a custom back button at the bottom
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Company Dashboard", key="back_to_company_dashboard_from_tender", use_container_width=True, type="primary"):
            # Clear tender detail state
            st.session_state.view_tender_detail = None
            st.session_state.page = "company_dashboard"
            st.session_state.tender_detail_source = None
            st.rerun()

def render_company_overview(company_id: int):
    """Render company statistics and overview"""
    st.markdown("### 📊 Company Overview")
    
    db = get_db_manager()
    
    # Get company stats using CRUD method
    stats = db.get_company_stats(company_id)
    
    # Get subscription info
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
    
    # ===== RECENT ANALYSES =====
    st.markdown("### 📋 Recent Analyses")
    
    # Get recent analyses using CRUD method
    analyses = db.get_company_tender_analyses(company_id, limit=5)
    
    if analyses:
        # Convert to DataFrame with selection support
        df_data = []
        for idx, analysis in enumerate(analyses):
            status_color = {
                'won': '🟢 Won',
                'lost': '🔴 Lost',
                'under_review': '🟠 Under Review',
                'submitted': '🔵 Submitted',
                'draft': '⚪ Draft'
            }.get(analysis.get('bid_status', 'draft'), analysis.get('bid_status', 'draft'))
            
            df_data.append({
                'id': analysis.get('id'),
                'tender_id': analysis.get('tender_id', 'N/A'),
                'tender_title': str(analysis.get('tender_title', ''))[:50],
                'recommended_bid': analysis.get('recommended_bid'),
                'confidence_score': analysis.get('confidence_score'),
                'analysis_date': str(analysis.get('analysis_date', ''))[:10] if analysis.get('analysis_date') else '',
                'bid_status': status_color,
                '_record': analysis
            })
        
        df = pd.DataFrame(df_data)
        
        display_columns = ['tender_id', 'tender_title', 'recommended_bid', 'confidence_score', 'analysis_date', 'bid_status']
        
        event = st.dataframe(
            df[display_columns],
            selection_mode="single-row",
            on_select="rerun",
            use_container_width=True,
            hide_index=True,
            column_config={
                "tender_id": st.column_config.Column("Tender ID", width="medium"),
                "tender_title": st.column_config.Column("Title", width="large"),
                "recommended_bid": st.column_config.Column("Recommended Bid", width="medium"),
                "confidence_score": st.column_config.Column("Confidence", width="small"),
                "analysis_date": st.column_config.Column("Date", width="small"),
                "bid_status": st.column_config.Column("Status", width="small"),
            }
        )
        
        # ===== HANDLE SELECTION - OPEN ANALYSIS DETAIL =====
        if event.selection and event.selection['rows']:
            selected_idx = event.selection['rows'][0]
            if selected_idx < len(df):
                row_data = df.iloc[selected_idx]
                analysis_id = row_data.get('id')
                if analysis_id:
                    st.session_state.comp_selected_analysis_id = analysis_id
                    st.session_state.comp_view = "analysis_detail"
                    st.rerun()
    else:
        st.info("No analyses found. Start analyzing tenders to see insights here.")


def render_analysis_detail_view(db, company_id: int, analysis_id: int):
    """Render detailed view for a tender analysis"""
    
    analysis = db.get_tender_analysis_by_id(analysis_id)
    
    if not analysis:
        st.error("Analysis not found")
        if st.button("← Back to Overview", key="comp_back_from_analysis"):
            st.session_state.comp_view = "overview"
            st.session_state.comp_selected_analysis_id = None
            st.rerun()
        return
    
    st.markdown("---")
    st.markdown("### 📊 Analysis Detail")
    
    # ===== BACK BUTTON =====
    if st.button("← Back to Overview", key="comp_back_analysis_to_overview"):
        st.session_state.comp_view = "overview"
        st.session_state.comp_selected_analysis_id = None
        st.rerun()
    
    st.divider()
    
    # ===== TENDER INFORMATION =====
    st.markdown("#### 📋 Tender Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Tender ID:** {analysis.get('tender_id', 'N/A')}")
        st.markdown(f"**Title:** {analysis.get('tender_title', 'N/A')}")
        st.markdown(f"**Procuring Entity:** {analysis.get('procuring_entity', 'N/A')}")
        st.markdown(f"**Division:** {analysis.get('division', 'N/A')}")
        st.markdown(f"**District:** {analysis.get('district', 'N/A')}")
        st.markdown(f"**Construction Type:** {analysis.get('construction_type', 'N/A')}")
    
    with col2:
        st.markdown(f"**Official Estimate:** {analysis.get('official_estimate', 'N/A')}")
        st.markdown(f"**Recommended Bid:** {analysis.get('recommended_bid', 'N/A')}")
        st.markdown(f"**Actual Bid:** {analysis.get('actual_bid', 'N/A')}")
        st.markdown(f"**Final Submitted Bid:** {analysis.get('final_submitted_bid', 'N/A')}")
        st.markdown(f"**Is Final Submitted:** {'✅ Yes' if analysis.get('is_final_submitted') else '❌ No'}")
    
    st.divider()
    
    # ===== ANALYSIS METRICS =====
    st.markdown("#### 📊 Analysis Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Confidence Score", f"{analysis.get('confidence_score', 0):.1f}%")
    with col2:
        st.metric("Success Probability", f"{analysis.get('success_probability', 0):.1f}%")
    with col3:
        st.metric("Expected Profit", analysis.get('expected_profit', 'N/A'))
    with col4:
        st.metric("Risk Level", analysis.get('risk_level', 'N/A'))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Bid Status", analysis.get('bid_status', 'N/A').title())
    with col2:
        st.metric("Competitor Count", analysis.get('competitor_count', 0))
    with col3:
        st.metric("Bid Accuracy Score", f"{analysis.get('bid_accuracy_score', 0):.1f}%")
    with col4:
        st.metric("NPPI Factor", analysis.get('nppi_factor', 'N/A'))
    
    st.divider()
    
    # ===== COMPETITOR INFORMATION =====
    if analysis.get('competitor_bids'):
        st.markdown("#### 🏢 Competitor Bids")
        try:
            competitor_data = json.loads(analysis.get('competitor_bids')) if isinstance(analysis.get('competitor_bids'), str) else analysis.get('competitor_bids')
            if competitor_data:
                df = pd.DataFrame(competitor_data) if isinstance(competitor_data, list) else pd.DataFrame([competitor_data])
                st.dataframe(df, use_container_width=True, hide_index=True)
        except:
            st.text(analysis.get('competitor_bids'))
    
    # ===== RISK STRATEGY =====
    if analysis.get('risk_strategy'):
        st.markdown("#### 🛡️ Risk Strategy")
        st.info(analysis.get('risk_strategy'))
    
    # ===== LESSONS LEARNED =====
    if analysis.get('lessons_learned'):
        st.markdown("#### 📝 Lessons Learned")
        st.success(analysis.get('lessons_learned'))
    
    # ===== ACTUAL RESULT =====
    if analysis.get('actual_winning_bid') or analysis.get('actual_winner'):
        st.divider()
        st.markdown("#### 🏆 Actual Result")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Winning Bid:** {analysis.get('actual_winning_bid', 'N/A')}")
            st.markdown(f"**Winner:** {analysis.get('actual_winner', 'N/A')}")
        with col2:
            st.markdown(f"**Our Rank:** {analysis.get('our_rank_actual', 'N/A')}")
            st.markdown(f"**Total Bidders:** {analysis.get('total_bidders_actual', 'N/A')}")
        
        if analysis.get('bid_accuracy_score'):
            st.metric("Bid Accuracy Score", f"{analysis.get('bid_accuracy_score', 0):.1f}%")

def render_team_management(company_id: int):
    """Manage users within the company"""
    
    st.markdown("### 👥 Team Management")
    st.caption("Add, edit, and manage team members for your company")
    
    db = get_db_manager()
    
    # Check if we're in detail view
    if st.session_state.comp_view == "user_detail":
        render_team_member_detail(db, company_id)
        return
    
    # Get current company users
    users = db.get_all_users(company_id=company_id)
    
    # ===== ADD NEW USER SECTION =====
    with st.expander("➕ Add Team Member", expanded=False):
        render_add_team_member_form(db, company_id)
    
    # ===== TEAM MEMBERS LIST =====
    total_users = len(users) if users else 0
    st.markdown(f"**Team Members ({total_users})**")
    
    if not users:
        st.info("No team members found")
        return
    
    # Convert to DataFrame for display
    df_data = []
    for user in users:
        # Skip showing company admins from other companies
        if user.get('role') == 'company_admin' and user.get('id') != st.session_state.user_id:
            continue
        
        is_active = user.get('is_active', 0)
        
        df_data.append({
            'id': user.get('id'),
            'full_name': user.get('full_name', 'Unknown'),
            'username': user.get('username', 'N/A'),
            'email': user.get('email', 'N/A'),
            'role': user.get('role', 'viewer').title(),
            'status': '🟢 Active' if is_active == 1 else '🔴 Inactive',
            'created_at': user.get('created_at', ''),
            '_record': user
        })
    
    df = pd.DataFrame(df_data)
    
    # Display DataFrame with selection
    display_columns = ['full_name', 'username', 'email', 'role', 'status']
    
    event = st.dataframe(
        df[display_columns],
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        column_config={
            "full_name": st.column_config.Column("Full Name", width="medium"),
            "username": st.column_config.Column("Username", width="medium"),
            "email": st.column_config.Column("Email", width="large"),
            "role": st.column_config.Column("Role", width="small"),
            "status": st.column_config.Column("Status", width="small"),
        }
    )
    
    # Handle selection
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            user_id = row_data.get('id')
            if user_id:
                st.session_state.comp_selected_user_id = user_id
                st.session_state.comp_view = "user_detail"
                st.rerun()


def render_add_team_member_form(db, company_id: int):
    """Render add team member form"""
    
    with st.form("add_company_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name *", key="add_user_full_name")
            email = st.text_input("Email *", key="add_user_email")
            username = st.text_input("Username *", key="add_user_username")
        
        with col2:
            role = st.selectbox(
                "Role *",
                options=["manager", "analyst", "viewer"],
                key="add_user_role"
            )
            phone = st.text_input("Phone", key="add_user_phone")
            generate_password = st.checkbox("Auto-generate password", key="add_user_gen_pwd")
            
            if not generate_password:
                password = st.text_input("Password *", type="password", key="add_user_password")
                confirm_password = st.text_input("Confirm Password *", type="password", key="add_user_confirm")
        
        submitted = st.form_submit_button("Add Team Member", type="primary")
        
        if submitted:
            # ===== VALIDATION =====
            errors = []
            
            if not full_name:
                errors.append("Full name is required")
            elif len(full_name.strip()) < 2:
                errors.append("Full name must be at least 2 characters")
            
            if not email:
                errors.append("Email is required")
            else:
                is_valid, err_msg = validate_email(email.strip())
                if not is_valid:
                    errors.append(f"Email: {err_msg}")
            
            if not username:
                errors.append("Username is required")
            else:
                is_valid, err_msg = validate_username(username.strip())
                if not is_valid:
                    errors.append(f"Username: {err_msg}")
            
            if not generate_password:
                if not password:
                    errors.append("Password is required")
                elif len(password) < 8:
                    errors.append("Password must be at least 8 characters")
                elif password != confirm_password:
                    errors.append("Passwords do not match")
            
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                # Generate password if auto
                if generate_password:
                    import secrets
                    password = secrets.token_urlsafe(12)
                
                user_data = {
                    'username': username.strip(),
                    'password': password,
                    'email': email.strip(),
                    'full_name': full_name.strip(),
                    'phone': phone.strip() if phone else '',
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
                    st.error(f"❌ Failed: {result}")


def render_team_member_detail(db, company_id: int):
    """Render detailed view for a team member"""
    
    user_id = st.session_state.comp_selected_user_id
    
    if not user_id:
        st.session_state.comp_view = "overview"
        st.rerun()
        return
    
    user = db.get_user_by_id(user_id)
    
    if not user:
        st.error("User not found")
        if st.button("← Back to Team", key="comp_back_to_team"):
            st.session_state.comp_view = "overview"
            st.rerun()
        return
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">✏️ Edit Team Member: {user.get('full_name', 'Unknown')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("← Back to Team List", key="comp_back_to_team_list"):
        st.session_state.comp_view = "overview"
        st.session_state.comp_selected_user_id = None
        st.rerun()
    
    st.divider()
    
    # ===== EDIT FORM =====
    with st.form(key="edit_team_member_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_full_name = st.text_input(
                "Full Name *",
                value=user.get('full_name', ''),
                key=f"comp_edit_name_{user_id}"
            )
            new_email = st.text_input(
                "Email *",
                value=user.get('email', ''),
                key=f"comp_edit_email_{user_id}"
            )
            new_phone = st.text_input(
                "Phone",
                value=user.get('phone', ''),
                key=f"comp_edit_phone_{user_id}"
            )
        
        with col2:
            new_role = st.selectbox(
                "Role *",
                options=["manager", "analyst", "viewer"],
                index=["manager", "analyst", "viewer"].index(user.get('role', 'viewer')) if user.get('role') in ["manager", "analyst", "viewer"] else 2,
                key=f"comp_edit_role_{user_id}"
            )
            
            new_active = st.checkbox(
                "Active",
                value=user.get('is_active', 1) == 1,
                key=f"comp_edit_active_{user_id}"
            )
        
        st.divider()
        
        # ===== FORM ACTIONS =====
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Save Changes",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if user.get('id') != st.session_state.user_id:
                delete_clicked = st.form_submit_button(
                    "🗑️ Remove User",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    st.warning("⚠️ Are you sure you want to remove this user?")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Confirm Remove", key=f"comp_confirm_delete_{user_id}"):
                            if db.delete_user(user_id):
                                st.success("User removed successfully!")
                                st.session_state.comp_view = "overview"
                                st.session_state.comp_selected_user_id = None
                                st.rerun()
                            else:
                                st.error("Failed to remove user")
                    with col_cancel:
                        if st.button("❌ Cancel", key="comp_cancel_delete"):
                            st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.comp_view = "overview"
                st.session_state.comp_selected_user_id = None
                st.rerun()
    
    # ===== PROCESS FORM SUBMISSION =====
    if submitted:
        updates = {}
        validation_errors = []
        
        # Validate full name
        if new_full_name:
            name_clean = safe_strip(new_full_name)
            if len(name_clean) < 2:
                validation_errors.append("Full name must be at least 2 characters")
            else:
                updates['full_name'] = name_clean
        else:
            validation_errors.append("Full name is required")
        
        # Validate email
        if new_email:
            email_clean = safe_strip(new_email)
            is_valid, err_msg = validate_email(email_clean)
            if not is_valid:
                validation_errors.append(f"Email: {err_msg}")
            else:
                updates['email'] = email_clean
        else:
            validation_errors.append("Email is required")
        
        if new_phone:
            updates['phone'] = safe_strip(new_phone)
        
        updates['role'] = new_role
        updates['is_active'] = 1 if new_active else 0
        
        if validation_errors:
            for err in validation_errors:
                st.error(f"❌ {err}")
        else:
            # Check for duplicates (excluding current user)
            duplicate_errors = []
            
            # Check email duplicate
            existing_email = db.query_one(
                "SELECT id FROM users WHERE email = ? AND id != ? AND company_id = ?",
                (updates['email'], user_id, company_id)
            )
            if existing_email:
                duplicate_errors.append(f"Email '{updates['email']}' is already used by another team member")
            
            if duplicate_errors:
                for err in duplicate_errors:
                    st.error(f"❌ {err}")
            else:
                if db.update_user(user_id, updates):
                    st.success("✅ User updated successfully!")
                    st.balloons()
                    st.session_state.comp_view = "overview"
                    st.session_state.comp_selected_user_id = None
                    st.rerun()
                else:
                    st.error("❌ Failed to update user")
    
    # ===== RESET PASSWORD SECTION =====
    st.divider()
    st.markdown("### 🔑 Reset Password")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔑 Reset Password", key=f"comp_reset_pwd_{user_id}", use_container_width=True):
            success, new_pw = db.reset_user_password(user_id)
            if success:
                st.success(f"✅ New password: `{new_pw}`")
            else:
                st.error(f"❌ Failed: {new_pw}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_company_tenders(company_id: int):
    """Manage tenders specific to this company"""
    st.markdown("### 📋 Company Tenders")
    
    db = get_db_manager()
    
    # ===== FILTERS =====
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search = st.text_input(
            "🔍 Search tenders",
            placeholder="Tender ID, title, or entity...",
            key="comp_tender_search",
            label_visibility="collapsed"
        )
    
    with col2:
        status_filter = st.selectbox(
            "Status",
            options=["All", "draft", "submitted", "under_review", "evaluated", "won", "lost"],
            key="comp_tender_status_filter"
        )
    
    with col3:
        if st.button("➕ Create New Tender", key="comp_create_tender", type="primary", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()
    
    st.divider()
    
    # ===== FETCH TENDERS =====
    try:
        status = None if status_filter == "All" else status_filter
        tenders = db.get_company_tenders(company_id, status_filter=status, limit=100)
    except Exception as e:
        st.error(f"Error loading tenders: {e}")
        return
    
    if not tenders:
        st.info("No tenders found")
        return
    
    # ===== FILTER BY SEARCH =====
    if search:
        search_lower = search.lower()
        tenders = [
            t for t in tenders
            if search_lower in str(t.get('tender_id', '')).lower()
            or search_lower in str(t.get('tender_title', '')).lower()
            or search_lower in str(t.get('procuring_entity', '')).lower()
        ]
    
    if not tenders:
        st.info("No tenders match the search criteria")
        return
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tenders", len(tenders))
    with col2:
        submitted = len([t for t in tenders if t.get('bid_status') == 'submitted'])
        st.metric("Submitted", submitted)
    with col3:
        won = len([t for t in tenders if t.get('bid_status') == 'won'])
        st.metric("Won", won)
    with col4:
        lost = len([t for t in tenders if t.get('bid_status') == 'lost'])
        st.metric("Lost", lost)
    
    st.markdown("---")
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, tender in enumerate(tenders):
        status_display = tender.get('bid_status', 'draft').title()
        status_color = {
            'draft': '⚪ Draft',
            'submitted': '🔵 Submitted',
            'under_review': '🟠 Under Review',
            'evaluated': '🟣 Evaluated',
            'won': '🟢 Won',
            'lost': '🔴 Lost'
        }.get(tender.get('bid_status', 'draft'), tender.get('bid_status', 'draft').title())
        
        df_data.append({
            'id': tender.get('id'),
            'tender_id': tender.get('tender_id', 'N/A'),
            'tender_title': str(tender.get('tender_title', ''))[:60],
            'procuring_entity': str(tender.get('procuring_entity', ''))[:30],
            'official_estimate': tender.get('official_estimate'),
            'status': status_color,
            'status_raw': tender.get('bid_status', 'draft'),
            'submission_deadline': str(tender.get('submission_deadline', ''))[:10] if tender.get('submission_deadline') else '',
            'created_at': str(tender.get('created_at', ''))[:10] if tender.get('created_at') else '',
            '_record': tender
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['tender_id', 'tender_title', 'procuring_entity', 'official_estimate', 'status', 'submission_deadline']
    
    event = st.dataframe(
        df[display_columns],
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        column_config={
            "tender_id": st.column_config.Column("Tender ID", width="medium"),
            "tender_title": st.column_config.Column("Title", width="large"),
            "procuring_entity": st.column_config.Column("Entity", width="medium"),
            "official_estimate": st.column_config.Column("Estimate (BDT)", width="medium"),
            "status": st.column_config.Column("Status", width="small"),
            "submission_deadline": st.column_config.Column("Deadline", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION - FIXED =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            tender_record = row_data.get('_record')
            if tender_record:
                # ✅ Set both tender_view and selected_id for direct detail view
                st.session_state.tender_view = "detail"
                st.session_state.tender_selected_id = tender_record.get('id')
                st.session_state.view_tender_detail = tender_record
                st.session_state.page = "tender_management"
                st.rerun()


def render_tender_detail_view(db, company_id: int, tender_id: str):
    """Render detailed view for a tender"""
    
    tender = db.get_tender_by_id(tender_id, company_id)
    
    if not tender:
        st.error("Tender not found")
        return
    
    st.markdown("---")
    st.markdown(f"### 📄 Tender Details: {tender.get('tender_id', 'N/A')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Title:** {tender.get('tender_title', 'N/A')}")
        st.markdown(f"**Procuring Entity:** {tender.get('procuring_entity', 'N/A')}")
        st.markdown(f"**Official Estimate:** {tender.get('official_estimate', 'N/A')}")
        st.markdown(f"**Status:** {tender.get('bid_status', 'draft').title()}")
        st.markdown(f"**Our Bid Amount:** {tender.get('our_bid_amount', 'N/A')}")
    
    with col2:
        st.markdown(f"**Division:** {tender.get('division', 'N/A')}")
        st.markdown(f"**District:** {tender.get('district', 'N/A')}")
        st.markdown(f"**Deadline:** {tender.get('submission_deadline', 'N/A')}")
        st.markdown(f"**Bid Submitted By:** {tender.get('submitted_by_name', 'N/A')}")
        st.markdown(f"**Bid Submitted Date:** {tender.get('bid_submission_date', 'N/A')}")
    
    # ===== ANALYSES SECTION =====
    st.markdown("---")
    st.markdown("### 📊 Tender Analyses")
    
    analyses = db.get_company_tender_analyses(company_id, tender_id=tender_id)
    
    if analyses:
        df = pd.DataFrame(analyses)
        display_cols = ['recommended_bid', 'confidence_score', 'analysis_date', 'bid_status']
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No analyses found for this tender")
    
    if st.button("← Back to Tenders", key="comp_back_to_tenders"):
        st.session_state.comp_selected_tender_id = None
        st.rerun()


def render_company_analytics(company_id: int):
    """Render analytics specific to this company"""
    st.markdown("### 📈 Company Analytics")
    
    db = get_db_manager()
    
    # Get analytics using CRUD method
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
        
        # ===== MONTHLY TREND =====
        st.markdown("### 📊 Monthly Trend")
        
        monthly_data = db.get_company_monthly_analytics(company_id, months=6)
        
        if monthly_data:
            df = pd.DataFrame(monthly_data)
            
            # ✅ CHECK: Verify columns exist before accessing
            if not df.empty and 'month' in df.columns:
                # Format for display
                display_df = df.copy()
                display_df['month'] = pd.to_datetime(display_df['month'])
                display_df['month'] = display_df['month'].dt.strftime('%b %Y')
                
                st.dataframe(
                    display_df[['month', 'count', 'avg_conf', 'wins']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "month": st.column_config.Column("Month", width="medium"),
                        "count": st.column_config.Column("Analyses", width="small"),
                        "avg_conf": st.column_config.Column("Avg Confidence", width="small"),
                        "wins": st.column_config.Column("Wins", width="small"),
                    }
                )
                
                # Show chart
                if len(df) > 1:
                    chart_df = df.copy()
                    chart_df['month'] = pd.to_datetime(chart_df['month'])
                    chart_df = chart_df.sort_values('month')
                    st.line_chart(chart_df.set_index('month')[['count', 'avg_conf', 'wins']])
            else:
                st.info("No monthly data available")
        else:
            st.info("Not enough data for monthly trends. Complete more analyses to see insights.")
    else:
        st.info("Not enough data for analytics. Complete more analyses to see insights.")
"""
Company User Management Module
Reusable user management for company admins
Uses the same grid/detail pattern as admin dashboard
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from utils.validators import (
    validate_username,
    validate_email,
    validate_bangladesh_mobile,
    normalize_mobile
)
from utils.helpers import safe_compare, safe_strip


def render_company_user_management(db, company_id: int):
    """
    Render user management for company admins
    Uses the same grid/detail pattern as admin dashboard
    """
    
    # Initialize session state for company user management
    if "comp_user_view" not in st.session_state:
        st.session_state.comp_user_view = "grid"
    if "comp_user_selected_id" not in st.session_state:
        st.session_state.comp_user_selected_id = None
    if "comp_user_search" not in st.session_state:
        st.session_state.comp_user_search = ""
    if "comp_user_sort_by" not in st.session_state:
        st.session_state.comp_user_sort_by = "full_name"
    if "comp_user_sort_order" not in st.session_state:
        st.session_state.comp_user_sort_order = "asc"
    
    # Route to appropriate view
    if st.session_state.comp_user_view == "detail":
        render_company_user_detail_view(db, company_id)
    else:
        render_company_user_grid_view(db, company_id)


def render_company_user_grid_view(db, company_id: int):
    """Render spreadsheet-style grid view for company users"""
    
    st.markdown("### 👥 Company Users")
    
    # ===== HEADER WITH ACTIONS =====
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("➕ Invite User", key="comp_user_add_btn", type="primary", use_container_width=True):
            st.session_state.comp_user_selected_id = None
            st.session_state.comp_user_view = "detail"
            st.rerun()
    
    with col2:
        st.session_state.comp_user_search = st.text_input(
            "🔍 Search",
            placeholder="Name, email, or username...",
            value=st.session_state.comp_user_search,
            key="comp_user_search_input",
            label_visibility="collapsed"
        )
    
    with col3:
        sort_by_map = {
            "Full Name": "full_name",
            "Username": "username",
            "Email": "email",
            "Role": "role",
            "Status": "is_active"
        }
        
        st.session_state.comp_user_sort_by = st.selectbox(
            "Sort by",
            options=list(sort_by_map.keys()),
            index=list(sort_by_map.values()).index(st.session_state.comp_user_sort_by) if st.session_state.comp_user_sort_by in sort_by_map.values() else 0,
            key="comp_user_sort_select",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # ===== FETCH USERS =====
    try:
        # Get users for this company
        users = db.get_all_users(company_id=company_id)
        
        # Apply search filter
        if st.session_state.comp_user_search:
            search_lower = st.session_state.comp_user_search.lower()
            users = [
                u for u in users
                if search_lower in str(u.get('username', '')).lower()
                or search_lower in str(u.get('email', '')).lower()
                or search_lower in str(u.get('full_name', '')).lower()
            ]
            
        total = len(users)
        
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return
    
    if not users:
        st.info("No users found. Click 'Invite User' to add team members.")
        return
    
    # ===== CONVERT TO DATAFRAME =====
    df_data = []
    for idx, user in enumerate(users):
        role_display = user.get('role', 'viewer').replace('_', ' ').title()
        is_active = user.get('is_active', 0)
        status_display = "✅ Active" if is_active == 1 else "❌ Inactive"
        is_approved = user.get('is_approved', 0)
        approved_display = "✅" if is_approved == 1 else "⏳ Pending"
        
        df_data.append({
            'id': user.get('id'),
            'username': user.get('username', 'N/A'),
            'full_name': user.get('full_name', 'N/A'),
            'email': user.get('email', 'N/A'),
            'role': role_display,
            'status': status_display,
            'is_active': is_active,
            'is_approved': is_approved,
            'approved': approved_display,
        })
    
    df = pd.DataFrame(df_data)
    
    # ===== SORT =====
    sort_column = st.session_state.comp_user_sort_by
    if sort_column in df.columns:
        sort_ascending = st.session_state.comp_user_sort_order == "asc"
        df = df.sort_values(by=sort_column, ascending=sort_ascending)
        df = df.reset_index(drop=True)
    
    # ===== DISPLAY METRICS =====
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", total)
    with col2:
        active = len([u for u in users if u.get('is_active', 0) == 1])
        st.metric("Active", active)
    with col3:
        approved = len([u for u in users if u.get('is_approved', 0) == 1])
        st.metric("Approved", approved)
    with col4:
        pending = len([u for u in users if u.get('is_approved', 0) == 0])
        st.metric("Pending", pending)
    
    st.markdown("---")
    
    # ===== DISPLAY DATAFRAME =====
    display_columns = ['id', 'username', 'full_name', 'email', 'role', 'status', 'approved']
    
    styled_df = df[display_columns].style
    
    def color_status(val):
        if 'Active' in str(val):
            return 'color: #065f46; background-color: #d1fae5;'
        elif 'Inactive' in str(val):
            return 'color: #991b1b; background-color: #fee2e2;'
        return ''
    
    styled_df = styled_df.map(color_status, subset=['status'])
    
    event = st.dataframe(
        styled_df,
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.Column("ID", width="small"),
            "username": st.column_config.Column("Username", width="medium"),
            "full_name": st.column_config.Column("Full Name", width="medium"),
            "email": st.column_config.Column("Email", width="large"),
            "role": st.column_config.Column("Role", width="small"),
            "status": st.column_config.Column("Status", width="small"),
            "approved": st.column_config.Column("Approved", width="small"),
        }
    )
    
    # ===== HANDLE SELECTION =====
    if event.selection and event.selection['rows']:
        selected_idx = event.selection['rows'][0]
        if selected_idx < len(df):
            row_data = df.iloc[selected_idx]
            user_id = row_data.get('id')
            if user_id:
                st.session_state.comp_user_selected_id = user_id
                st.session_state.comp_user_view = "detail"
                st.rerun()
    
    st.caption(f"Showing {len(users)} users")


def render_company_user_detail_view(db, company_id: int):
    """Render full-page detail view for company user management"""
    
    user_id = st.session_state.comp_user_selected_id
    is_new = user_id is None
    
    st.markdown('<div class="detail-container">', unsafe_allow_html=True)
    
    # ===== HEADER =====
    title = "➕ Invite New User" if is_new else f"✏️ Edit User Details (ID: {user_id})"
    st.markdown(f"""
    <div class="detail-header">
        <div class="detail-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("◀ Back to User List", key="comp_user_back_to_grid"):
        st.session_state.comp_user_view = "grid"
        st.session_state.comp_user_selected_id = None
        st.rerun()
    
    st.divider()
    
    # ===== GET USER DATA =====
    if is_new:
        user = {
            'id': None,
            'username': '',
            'full_name': '',
            'email': '',
            'mobile_number': '',
            'phone': '',
            'role': 'viewer',
            'is_active': 1,
            'is_approved': 0,
            'specialization': '',
            'years_experience': 0,
            'location': '',
            'website': '',
            'bio': '',
            'company_id': company_id,
            'company_name': ''
        }
    else:
        user = db.get_user_by_id(user_id)
        if not user:
            st.error(f"User with ID {user_id} not found")
            if st.button("Close", key="comp_user_close_not_found"):
                st.session_state.comp_user_view = "grid"
                st.session_state.comp_user_selected_id = None
                st.rerun()
            return
    
    # ===== EDIT FORM =====
    with st.form(key="comp_user_edit_form"):
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">👤 Account Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input(
                "Full Name *",
                value=user.get('full_name', ''),
                key="comp_user_edit_full_name"
            )
            
            username = st.text_input(
                "Username *",
                value=user.get('username', ''),
                key="comp_user_edit_username",
                help="3-30 characters, letters, numbers, and underscores only"
            )
            
            email = st.text_input(
                "Email Address *",
                value=user.get('email', ''),
                key="comp_user_edit_email",
                help="Valid email format required"
            )
        
        with col2:
            mobile = st.text_input(
                "Mobile Number *",
                value=user.get('mobile_number', ''),
                key="comp_user_edit_mobile",
                help="Bangladeshi mobile: 01XXXXXXXXX (11 digits)"
            )
            
            phone = st.text_input(
                "Phone",
                value=user.get('phone', ''),
                key="comp_user_edit_phone"
            )
            
            # Company is fixed for company users
            st.text_input(
                "Company",
                value=user.get('company_name', 'Your Company'),
                disabled=True,
                key="comp_user_edit_company"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PERMISSIONS & ACCESS =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">⚙️ Permissions & Access</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Company roles (excluding system_admin and individual)
            role_options = ["company_admin", "manager", "analyst", "estimator", "viewer"]
            current_role = user.get('role', 'viewer')
            
            if current_role not in role_options:
                role_options.append(current_role)
            
            try:
                role_index = role_options.index(current_role)
            except ValueError:
                role_index = 0
            
            role = st.radio(
                "System Role",
                options=role_options,
                index=role_index,
                key="comp_user_edit_role",
                help="Company users can have various roles based on their responsibilities."
            )
        
        with col2:
            is_active = st.radio(
                "Account Status",
                options=["Active", "Inactive"],
                index=0 if user.get('is_active', 0) == 1 else 1,
                key="comp_user_edit_status"
            )
            is_active_bool = is_active == "Active"
            
            if not is_new:
                is_approved = st.radio(
                    "Approval Status",
                    options=["Approved", "Pending"],
                    index=0 if user.get('is_approved', 0) == 1 else 1,
                    key="comp_user_edit_approved"
                )
                is_approved_bool = is_approved == "Approved"
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== PROFESSIONAL INFORMATION =====
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">💼 Professional Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            specialization = st.text_input(
                "Specialization",
                value=user.get('specialization', ''),
                key="comp_user_edit_specialization"
            )
            years_experience = st.number_input(
                "Years of Experience",
                min_value=0,
                max_value=50,
                value=user.get('years_experience', 0) or 0,
                key="comp_user_edit_years_exp"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value=user.get('location', ''),
                key="comp_user_edit_location"
            )
            website = st.text_input(
                "Website",
                value=user.get('website', ''),
                key="comp_user_edit_website"
            )
        
        bio = st.text_area(
            "Bio",
            value=user.get('bio', ''),
            max_chars=500,
            key="comp_user_edit_bio"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== FORM ACTIONS =====
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Save Changes",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if not is_new:
                delete_clicked = st.form_submit_button(
                    "🗑️ Remove User",
                    type="secondary",
                    use_container_width=True
                )
                if delete_clicked:
                    st.warning("⚠️ Are you sure you want to remove this user?")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Confirm Remove", key=f"comp_user_confirm_delete_{user_id}"):
                            if db.delete_user(user_id):
                                st.success("User removed successfully!")
                                st.session_state.comp_user_view = "grid"
                                st.session_state.comp_user_selected_id = None
                                st.rerun()
                            else:
                                st.error("Failed to remove user")
                    with col_cancel:
                        if st.button("❌ Cancel", key="comp_user_cancel_delete"):
                            st.rerun()
        
        with col3:
            if st.form_submit_button(
                "❌ Close / Cancel",
                use_container_width=True
            ):
                st.session_state.comp_user_view = "grid"
                st.session_state.comp_user_selected_id = None
                st.rerun()
    
    # ===== PROCESS FORM SUBMISSION =====
    if submitted:
        updates = {}
        validation_errors = []
        
        # Validate and process each field
        if full_name:
            full_name_clean = safe_strip(full_name)
            if len(full_name_clean) < 2:
                validation_errors.append("Full name must be at least 2 characters")
            else:
                updates['full_name'] = full_name_clean
        else:
            validation_errors.append("Full name is required")
        
        if username:
            username_clean = safe_strip(username)
            is_valid, error_msg = validate_username(username_clean)
            if not is_valid:
                validation_errors.append(f"Username: {error_msg}")
            else:
                updates['username'] = username_clean
        else:
            validation_errors.append("Username is required")
        
        if email:
            email_clean = safe_strip(email)
            is_valid, error_msg = validate_email(email_clean)
            if not is_valid:
                validation_errors.append(f"Email: {error_msg}")
            else:
                updates['email'] = email_clean
        else:
            validation_errors.append("Email is required")
        
        if mobile:
            mobile_clean = safe_strip(mobile)
            normalized_mobile = normalize_mobile(mobile_clean)
            if not validate_bangladesh_mobile(normalized_mobile):
                validation_errors.append("Invalid mobile number. Must be a valid Bangladeshi number (01XXXXXXXXX)")
            else:
                updates['mobile_number'] = normalized_mobile
        else:
            validation_errors.append("Mobile number is required")
        
        if phone:
            updates['phone'] = safe_strip(phone)
        
        updates['role'] = role
        updates['is_active'] = 1 if is_active_bool else 0
        updates['company_id'] = company_id
        
        if not is_new:
            updates['is_approved'] = 1 if is_approved_bool else 0
        
        if specialization:
            updates['specialization'] = safe_strip(specialization)
        updates['years_experience'] = years_experience if years_experience > 0 else None
        
        if location:
            updates['location'] = safe_strip(location)
        if website:
            updates['website'] = safe_strip(website)
        if bio:
            updates['bio'] = safe_strip(bio)
        
        # Show validation errors
        if validation_errors:
            for err in validation_errors:
                st.error(f"❌ {err}")
        else:
            # ============================================================
            # DUPLICATE CHECKING
            # ============================================================
            duplicate_errors = []
            exclude_id = None if is_new else user_id
            
            # Check username duplicate
            if db.check_username_exists(updates['username'], exclude_id):
                duplicate_errors.append(f"Username '{updates['username']}' is already taken")
            
            # Check email duplicate
            if db.check_email_exists(updates['email'], exclude_id):
                duplicate_errors.append(f"Email '{updates['email']}' is already registered")
            
            # Check mobile duplicate
            if db.check_mobile_exists(updates['mobile_number'], exclude_id):
                duplicate_errors.append(f"Mobile number '{updates['mobile_number']}' is already registered")
            
            if duplicate_errors:
                for err in duplicate_errors:
                    st.error(f"❌ {err}")
            else:
                # Save to database
                if is_new:
                    # Create new user in this company
                    user_data = {
                        'username': updates['username'],
                        'email': updates['email'],
                        'full_name': updates['full_name'],
                        'phone': updates.get('phone', ''),
                        'mobile_number': updates['mobile_number'],
                        'role': updates['role'],
                        'password': 'Temporary@123'  # Will need to be reset
                    }
                    success, result = db.create_company_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        st.success(f"✅ User {updates['full_name']} invited successfully!")
                        st.info(f"📧 An invitation email will be sent to {updates['email']}")
                        st.session_state.comp_user_view = "grid"
                        st.session_state.comp_user_selected_id = None
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create user: {result}")
                else:
                    if db.update_user(user_id, updates):
                        st.success("✅ User updated successfully!")
                        st.balloons()
                        st.session_state.comp_user_view = "grid"
                        st.session_state.comp_user_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to update user")
    
    st.markdown('</div>', unsafe_allow_html=True)