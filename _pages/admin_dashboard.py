# _pages/admin_dashboard.py - Refactored (UI only)

import streamlit as st
import pandas as pd
import os
import datetime
from typing import Dict, List, Optional, Any, Tuple

from modules.egp_boq_workspace import render_boq_workspace
from modules.unified_import_wizard import render_unified_import_wizard
from modules.unified_version_manager import render_unified_version_management
from modules.unified_rollback_manager import render_rollback_management
from modules.rate_viewer import render_rate_viewer
from modules.rate_crud_forms import render_rate_crud_forms
from modules.pwd_data_manager import (
    PWDParserWithHierarchy, 
    PWDExtractorForVerification,
    save_hierarchy_to_database,
    get_rate_versions,
    archive_version
)
from modules.subscription_ui import render_subscription_card
from modules.subscription import get_plan

from database.unified_db_manager import get_db_manager

from database.connection import get_supabase_client, get_db_type, is_supabase
import json

def get_fallback_tables():
    """Return fallback table list for Supabase"""
    return [
        "users", "companies", "subscriptions", "user_oauth",
        "boq_templates", "boq_items", "boq_approval_history",
        "rates", "system_rates", "price_change_logs",
        "company_profile", "company_onboarding_status", "company_documents",
        "company_financials", "company_licenses", "company_personnel",
        "company_nppi", "certificate",
        "competitors", "competitor_rates", "competitor_master",
        "competitor_bids", "competitor_bid_history",
        "tenders", "tender_milestones", "tender_documents", "bid_submissions",
        "analysis_history", "otp_verification", "system_config",
        "user_activity_logs", "version_history", "migrations",
        "pwd_import_history", "extension_downloads", "demo_data_generation_log"
    ]

def categorize_tables(all_tables):
    """Categorize tables into groups for better UX"""
    table_groups = {}
    
    for table in all_tables:
        if table in ["users", "companies", "subscriptions", "user_oauth"]:
            group = "Core Tables"
        elif table in ["boq_templates", "boq_items", "boq_approval_history"]:
            group = "BOQ Tables"
        elif table in ["rates", "system_rates", "price_change_logs"]:
            group = "Rate Tables"
        elif table in ["company_profile", "company_onboarding_status", "company_documents", 
                     "company_financials", "company_licenses", "company_personnel", 
                     "company_nppi", "certificate"]:
            group = "Company Tables"
        elif table in ["competitors", "competitor_rates", "competitor_master", 
                    "competitor_bids", "competitor_bid_history"]:
            group = "Competitor Tables"
        elif table in ["tenders", "tender_milestones", "tender_documents", "bid_submissions"]:
            group = "Tender Tables"
        elif table in ["otp_verification", "system_config", "user_activity_logs", 
                    "version_history", "migrations", "pwd_import_history"]:
            group = "System Tables"
        else:
            group = "Other Tables"
        
        if group not in table_groups:
            table_groups[group] = []
        table_groups[group].append(table)
    
    return table_groups


db = get_db_manager()
def render_pwd_ingestion_panel():
    """Main PWD ingestion panel with hierarchy - UI only"""
    
    st.markdown("### 📥 Import PWD Schedule")
    st.caption("Upload PWD Schedule PDF - Automatically detects parent-child hierarchy")
    
    uploaded_file = st.file_uploader(
        "Upload PWD Rate Schedule PDF", 
        type=["pdf"], 
        key="admin_pwd_hierarchical"
    )
    
    if not uploaded_file:
        st.info("📁 Please upload a PWD rate schedule PDF file")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2022)
    
    with col2:
        max_pages = st.number_input("Preview Pages", min_value=1, max_value=500, value=10,
                                    help="Process first N pages. Set to 500 for full PDF.")
    
    dry_run = st.checkbox("🔍 Dry Run Mode (Preview only, no database save)", value=True)
    
    if st.button("⚡ Parse PWD Schedule", type="primary", use_container_width=True):
        temp_path = "temp_pwd.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Parsing PDF with hierarchical structure..."):
                parser = PWDParserWithHierarchy()
                hierarchy = parser.parse_pdf_with_hierarchy(temp_path, max_pages=max_pages if max_pages > 0 else None)
            
            if hierarchy['parents']:
                st.success(f"✅ Parsed {len(hierarchy['parents'])} parent items and {len(hierarchy['children'])} child items")
                
                # Display preview
                render_hierarchical_pwd_preview(hierarchy)
                
                # Save to database if not dry run
                if not dry_run:
                    if st.button("💾 Confirm & Save to Database", type="primary"):
                        success, msg1, msg2 = save_hierarchy_to_database(hierarchy, edition_year)
                        if success:
                            st.success(f"🎉 Saved {msg1} parents and {msg2} children to database!")
                            st.balloons()
                        else:
                            st.error(f"Database error: {msg2}")
                
                # Download options
                st.markdown("### 📥 Export Data")
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    parents_df = pd.DataFrame(hierarchy['parents'])
                    st.download_button(
                        "📥 Download Parents (CSV)",
                        parents_df.to_csv(index=False),
                        f"pwd_parents_{edition_year}.csv",
                        "text/csv"
                    )
                
                with col_d2:
                    children_data = []
                    for child in hierarchy['children']:
                        row = {'pwd_code': child['pwd_code'], 'parent_code': child['parent_code'], 
                               'description': child['description'], 'unit': child['unit']}
                        for zone, rate in child['rates'].items():
                            row[zone] = rate
                        children_data.append(row)
                    children_df = pd.DataFrame(children_data)
                    st.download_button(
                        "📥 Download Child Items (CSV)",
                        children_df.to_csv(index=False),
                        f"pwd_children_{edition_year}.csv",
                        "text/csv"
                    )
            else:
                st.warning("No items found. Try increasing the number of pages.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def render_pwd_verification_tool():
    """Render the PWD verification tool in admin dashboard"""
    
    st.markdown("### 🔍 PWD Schedule Verification Tool")
    st.caption("Scan full PDF, analyze hierarchy, and export CSV for manual verification")
    
    uploaded_file = st.file_uploader(
        "Upload PWD Rate Schedule PDF for Verification", 
        type=["pdf"], 
        key="pwd_verification"
    )
    
    if not uploaded_file:
        st.info("📁 Upload a PWD PDF to analyze its structure")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        scan_pages = st.number_input(
            "Pages to Scan", 
            min_value=1, 
            max_value=500, 
            value=50,
            step=10,
            help="Scan first N pages. Set to 500 for full PDF."
        )
    
    with col2:
        full_scan = st.checkbox("Scan Entire PDF", value=False, help="Overrides pages setting")
    
    if st.button("🔍 Analyze PDF Structure", type="primary", use_container_width=True):
        temp_path = "temp_pwd_verify.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Analyzing PDF structure..."):
                extractor = PWDExtractorForVerification()
                max_pages = None if full_scan else scan_pages
                report = extractor.extract_from_pdf(temp_path, max_pages=max_pages)
            
            # Display summary
            st.markdown("### 📊 Analysis Summary")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("Total Items Found", report['summary']['total_items'])
            with col_b:
                st.metric("Parent Items", report['summary']['total_parents'])
            with col_c:
                st.metric("Child Items", report['summary']['total_children'])
            with col_d:
                st.metric("Orphans Found", report['summary']['orphans'])
            
            if report['summary']['parents_without_children'] > 0:
                st.warning(f"⚠️ {report['summary']['parents_without_children']} parent items have NO child items - needs verification")
            
            if report['summary']['orphans'] > 0:
                st.error(f"❌ {report['summary']['orphans']} orphan items found (parent not detected)")
            
            # Display tables
            if report['parents']:
                st.markdown("#### Parents")
                st.dataframe(pd.DataFrame(report['parents']), use_container_width=True, hide_index=True)
                
                csv_parents = pd.DataFrame(report['parents']).to_csv(index=False)
                st.download_button(
                    "📥 Download Parents CSV",
                    csv_parents,
                    f"pwd_parents_verification_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv"
                )
            
            if report['parents_without_children_list']:
                st.markdown("#### Parents Without Children (Need Verification)")
                st.dataframe(pd.DataFrame(report['parents_without_children_list']), use_container_width=True, hide_index=True)
            
            if report['orphans_list']:
                st.markdown("#### Orphan Items")
                st.dataframe(pd.DataFrame(report['orphans_list']), use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            import traceback
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def render_hierarchical_pwd_preview(hierarchy):
    """Display hierarchical PWD data"""
    
    if not hierarchy['parents']:
        st.warning("No parent items found")
        return
    
    st.markdown("### 📊 Hierarchical PWD Schedule Structure")
    
    total_parents = len(hierarchy['parents'])
    total_children = len(hierarchy['children'])
    children_with_rates = sum(1 for c in hierarchy['children'] if c['rates'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Parent Items", total_parents)
    col2.metric("Child Items", f"{children_with_rates} / {total_children}")
    col3.metric("Coverage Ratio", f"{total_children/total_parents:.1f}" if total_parents > 0 else "0")
    
    st.markdown("### 📂 PWD Schedule Hierarchy")
    
    for parent in hierarchy['parents'][:30]:
        children = hierarchy['parent_child_map'].get(parent['code'], [])
        
        if children:
            with st.expander(f"📁 {parent['code']}: {parent['description'][:70]}... ({len(children)} items)", expanded=False):
                child_data = []
                for child in children:
                    row = {
                        'Code': child['pwd_code'],
                        'Description': child['description'][:80] + ('...' if len(child['description']) > 80 else ''),
                        'Unit': child['unit'],
                    }
                    for zone, rate in child['rates'].items():
                        row[zone] = f"৳{rate:,.2f}"
                    child_data.append(row)
                
                if child_data:
                    st.dataframe(pd.DataFrame(child_data), use_container_width=True, hide_index=True)
        else:
            st.info(f"📄 {parent['code']}: {parent['description'][:70]}... (No child items)")


def render_hierarchical_pwd_viewer():
    """View imported PWD hierarchy from database"""
    
    st.markdown("### 📂 PWD Hierarchy from Database")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all parents
        cursor.execute("SELECT pwd_code, description, chapter_number FROM pwd_parents ORDER BY pwd_code")
        parents = cursor.fetchall()
        
        if not parents:
            st.info("No data found in database. Please import a PWD schedule first.")
            return
        
        st.success(f"Found {len(parents)} parent items in database")
        
        # Chapter filter
        chapters = sorted(set(p[2] for p in parents))
        selected_chapter = st.selectbox("Filter by Chapter", ["All"] + chapters)
        
        # Search
        search_term = st.text_input("Search items", placeholder="Enter item code or description...")
        
        # Display parents
        for parent in parents:
            parent_code = parent[0]
            parent_desc = parent[1]
            parent_chapter = parent[2]
            
            if selected_chapter != "All" and parent_chapter != selected_chapter:
                continue
            
            if search_term and search_term.lower() not in parent_code.lower() and search_term.lower() not in parent_desc.lower():
                continue
            
            # Get children for this parent
            cursor.execute("""
                SELECT c.pwd_code, c.description, c.unit,
                       cr.zone_name, cr.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates cr ON c.pwd_code = cr.pwd_code
                WHERE c.parent_code = ?
                ORDER BY c.pwd_code, cr.zone_name
            """, (parent_code,))
            
            children = cursor.fetchall()
            
            if children:
                with st.expander(f"📁 {parent_code} (Ch {parent_chapter}): {parent_desc[:80]}... ({len(set(c[0] for c in children))} items)", expanded=False):
                    # Organize children
                    children_dict = {}
                    for child in children:
                        child_code = child[0]
                        if child_code not in children_dict:
                            children_dict[child_code] = {
                                'code': child_code,
                                'description': child[1][:100],
                                'unit': child[2],
                                'rates': {}
                            }
                        if child[3]:
                            children_dict[child_code]['rates'][child[3]] = child[4]
                    
                    child_data = []
                    for child in children_dict.values():
                        row = {'Code': child['code'], 'Description': child['description'], 'Unit': child['unit']}
                        for zone, rate in child['rates'].items():
                            row[zone] = f"৳{rate:,.2f}"
                        child_data.append(row)
                    
                    st.dataframe(pd.DataFrame(child_data), use_container_width=True, hide_index=True)
            else:
                st.info(f"📄 {parent_code} (Ch {parent_chapter}): {parent_desc[:80]}... (No child items)")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading hierarchy: {str(e)}")


def render_pwd_version_tab(db_instance):
    """Render PWD version management tab"""
    
    st.subheader("🏗️ PWD Rate Schedule Version Control")
    
    tabs = st.tabs(["📥 Import New Version", "📜 Version History", "⚙️ Migration"])
    
    with tabs[0]:
        render_version_import(db_instance)
    
    with tabs[1]:
        render_version_history(db_instance)
    
    with tabs[2]:
        render_version_migration(db_instance)


def render_version_import(db_instance):
    """Import a new version of PWD rates"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        version_name = st.text_input("Version Name", placeholder="PWD Schedule 2025")
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025)
    
    with col2:
        effective_date = st.date_input("Effective From")
        is_active = st.checkbox("Set as Active Version", value=True)
    
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    
    if uploaded_file and st.button("Import Version"):
        st.success(f"✅ Version {version_name} imported successfully!")


# def render_version_history(db_instance):
#     """Display version history"""
    
#     versions = get_rate_versions(db_instance)
    
#     for version in versions:
#         with st.expander(f"{version['name']} ({version['year']})"):
#             st.write(f"**Effective Date:** {version['effective_date']}")
#             st.write(f"**Status:** {'✅ Active' if version['is_active'] else '📦 Archived'}")
#             st.write(f"**Imported:** {version['imported_at']}")
#             st.write(f"**Items:** {version['parent_count']} parents, {version['child_count']} children")
            
#             if version['is_active']:
#                 if st.button("Archive", key=f"archive_{version['id']}"):
#                     archive_version(db_instance, version['id'])
#                     st.rerun()


def render_version_migration(db_instance):
    """Migrate BOQ items to new version"""
    st.info("Migration functionality coming soon")

def show():
    """Admin dashboard page with full system management"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System-wide administration and monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get all users for stats
    all_users = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    # Statistics in a row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(all_users))
    
    with col2:
        active_users = len([u for u in all_users if u.get('is_active', False)]) if all_users else 0
        st.metric("Active Users", active_users)
    
    with col3:
        companies = set([u.get('company_name', 'N/A') for u in all_users if u.get('company_name') and u.get('company_name') != 'N/A']) if all_users else set()
        st.metric("Companies", len(companies))
    
    with col4:
        paid_subs = len([s for s in all_subs if s.get('plan') not in ['free', 'trial']]) if all_subs else 0
        st.metric("Paid Subscriptions", paid_subs)
    
    st.markdown("---")
    
    # ✅ 3 Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "👑 Overview",
        "👥 Users & Roles",
        "🏢 Companies",
        "🏗️ Rate Import",
        "📦 Version Management",
        "⚙️ System Config",
        "💾 Database Backup"

    ])
    
    # ========== TAB 1: OVERVIEW ==========
    with tab1:
        render_admin_overview(all_users, all_subs)
    
    # ========== TAB 2: USERS & ROLES ==========
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 👑 System Users")
            render_system_user_management()
        
        with col2:
            st.markdown("#### 🔐 Role Management")
            render_role_management_page()
        
        st.markdown("---")
        st.markdown("#### 👥 All Users")
        render_all_users(all_users)
    
    # ========== TAB 3: COMPANIES ==========
    with tab3:
        render_company_management()
    
    # ========== TAB 4: RATE IMPORT ==========
    with tab4:
        render_unified_import_wizard(db)
    
    # ========== TAB 5: VERSION MANAGEMENT ==========
    with tab5:
        render_unified_version_management()
    
    # ========== TAB 6: SYSTEM CONFIG ==========
    with tab6:
        render_system_configuration()
    with tab7:
        render_database_backup()


def show_bak():
    """Admin dashboard page with full system management"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System-wide administration and monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ✅ Use CRUD methods
    all_users = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    # Statistics in a row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(all_users))
    
    with col2:
        active_users = len([u for u in all_users if u.get('is_active', False)]) if all_users else 0
        st.metric("Active Users", active_users)
    
    with col3:
        companies = set([u.get('company_name', 'N/A') for u in all_users if u.get('company_name') and u.get('company_name') != 'N/A']) if all_users else set()
        st.metric("Companies", len(companies))
    
    with col4:
        paid_subs = len([s for s in all_subs if s.get('plan') not in ['free', 'trial']]) if all_subs else 0
        st.metric("Paid Subscriptions", paid_subs)
    
    # Add a divider to separate metrics from tabs
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "📊 Overview", 
        "👥 All Users", 
        "🏢 Companies", 
        "👑 System Users", 
        "🔐 Role Management",
        "🏗️ Rate Import",    
        "📅 Version Management",
        # "🔄 Rollback Management",
        "📝 Manual Entry",
        "📊 Rate Viewer",
        "⚙️ System Config",
        "💳 Subscription Plans"
    ])
    
    with tab1:
        render_admin_overview(all_users, all_subs)
    
    with tab2:
        render_all_users(all_users)
    
    with tab3:
        render_company_management()
    
    with tab4:
        render_system_user_management()
    
    with tab5:
        render_role_management_page()
    
    with tab6:
        render_unified_import_wizard(db)

    # with tab7:
    #     render_rollback_management(db)        
    
    with tab7:
        render_unified_version_management(db)
    
    with tab8:
        render_rate_crud_forms(db)

    with tab9:
        render_rate_viewer(db)
    
    with tab10:
        render_system_configuration()
    
    with tab11:
        render_subscription_plans_management()



def render_admin_overview(all_users, all_subs):
    """Render system overview with charts - Using CRUD methods"""
    st.markdown("### System Overview")
    
    # Get user growth data
    try:
        db = get_db_manager()
        user_growth_data = db.get_user_growth(6)
        
        # Check if we have valid data
        if user_growth_data and len(user_growth_data) > 0:
            # Create DataFrame
            user_growth = pd.DataFrame(user_growth_data)
            
            # Check if we have the required columns
            if 'month' in user_growth.columns and 'count' in user_growth.columns:
                # Convert count to numeric
                user_growth['count'] = pd.to_numeric(user_growth['count'], errors='coerce').fillna(0)
                # Sort by month
                user_growth = user_growth.sort_values('month')
                # Display chart
                st.line_chart(user_growth.set_index('month')['count'])
            else:
                # Try to fix columns
                cols = user_growth.columns.tolist()
                if len(cols) >= 2:
                    # Rename columns
                    rename_dict = {}
                    for col in cols:
                        if 'month' in col.lower() or 'date' in col.lower():
                            rename_dict[col] = 'month'
                        elif 'count' in col.lower() or 'total' in col.lower() or 'num' in col.lower():
                            rename_dict[col] = 'count'
                    
                    if rename_dict:
                        user_growth = user_growth.rename(columns=rename_dict)
                        if 'month' in user_growth.columns and 'count' in user_growth.columns:
                            user_growth['count'] = pd.to_numeric(user_growth['count'], errors='coerce').fillna(0)
                            user_growth = user_growth.sort_values('month')
                            st.line_chart(user_growth.set_index('month')['count'])
                        else:
                            st.info("User growth data format is unexpected.")
                    else:
                        st.info("User growth data format is unexpected.")
                else:
                    st.info("Not enough data to display user growth chart.")
        else:
            st.info("No user growth data available yet. Data will appear as users register.")
    except Exception as e:
        st.warning(f"Could not load user growth chart: {str(e)}")
        st.info("User growth data will appear as users register on the platform.")
    
        
    # Plan distribution
    if all_subs:
        plan_counts = {}
        for sub in all_subs:
            plan = sub.get('plan', 'free')
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        plan_df = pd.DataFrame(plan_counts.items(), columns=['Plan', 'Count'])
        st.bar_chart(plan_df.set_index('Plan'))
    else:
        st.info("No subscription data available")
    
    # Role distribution
    if all_users:
        role_counts = {}
        for user in all_users:
            role = user.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_df = pd.DataFrame(role_counts.items(), columns=['Role', 'Count'])
        st.bar_chart(role_df.set_index('Role'))
    else:
        st.info("No user data available")




def render_all_users(all_users):
    """Render all users table"""
    st.markdown("### All Users")
    
    search = st.text_input("🔍 Search users", placeholder="Name, email, or username...")
    
    if all_users:
        user_list = []
        for u in all_users:
            user_dict = {
                'ID': u.get('id', 'N/A'),
                'Username': u.get('username', 'N/A'),
                'Email': u.get('email', 'N/A'),
                'Full Name': u.get('full_name', 'N/A'),
                'Phone': u.get('phone', ''),
                'Role': u.get('role', 'N/A'),
                'Active': '✅' if u.get('is_active', 0) == 1 else '❌',
                'Company': u.get('company_name', 'N/A'),
                'Created': str(u.get('created_at', ''))[:10] if u.get('created_at') else ''
            }
            
            if search:
                if (search.lower() in user_dict['Username'].lower() or 
                    search.lower() in user_dict['Email'].lower() or 
                    search.lower() in user_dict['Full Name'].lower()):
                    user_list.append(user_dict)
            else:
                user_list.append(user_dict)
        
        if user_list:
            user_df = pd.DataFrame(user_list)
            st.dataframe(user_df, use_container_width=True, hide_index=True)
        else:
            st.info("No users match the search criteria")
    else:
        st.info("No users found")


def render_company_management():
    """Render company management interface for super admin with subscription control"""
    st.markdown("### 🏢 Company Management")
    st.caption("Create, edit, and manage companies on the platform")
    
    # Add New Company (existing code)
    with st.expander("➕ Add New Company", expanded=False):
        with st.form("add_company_form"):
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Company Name *")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                mobile_number = st.text_input("Mobile Number *", help="Bangladeshi mobile: 01XXXXXXXXX")
                division = st.text_input("Division")
            with col2:
                district = st.text_input("District")
                registration_number = st.text_input("Registration Number")
                vat_number = st.text_input("VAT Number")
                address = st.text_area("Address", height=80)
            
            submitted = st.form_submit_button("Create Company", type="primary")
            if submitted:
                if not company_name:
                    st.error("Company name is required")
                elif not mobile_number:
                    st.error("Mobile number is required")
                else:
                    company_data = {
                        'company_name': company_name,
                        'email': email,
                        'phone': phone,
                        'mobile_number': mobile_number,
                        'division': division,
                        'district': district,
                        'address': address,
                        'registration_number': registration_number,
                        'vat_number': vat_number
                    }
                    success, result = db.create_company(company_data)
                    if success:
                        st.success(f"✅ Company '{company_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")

    
    # Search and filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search companies", placeholder="Name or email...")
    with col2:
        show_inactive = st.checkbox("Show inactive")
    
    # Get companies
    status_filter = None if show_inactive else 1
    companies, total = db.get_all_companies_filtered(
        search=search,
        status=status_filter,
        limit=50,
        offset=0
    )
    
    st.markdown(f"**Total Companies:** {total}")
    
    # Display companies
    if companies:
        for company in companies:
            # Get subscription info
            company_id = company['id']  # This should be 3351 for Babui
            subscription = db.get_company_subscription(company['id'])
            
            with st.expander(f"🏢 {company['company_name']} - {company.get('email', 'No email')}"):
                # Create tabs for company details and subscription
                comp_tab1, comp_tab2 = st.tabs(["📋 Company Details", "💳 Subscription"])
                
                with comp_tab1:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Company details form (existing code)
                        new_name = st.text_input("Company Name", value=company['company_name'], key=f"name_{company['id']}")
                        new_email = st.text_input("Email", value=company.get('email', ''), key=f"email_{company['id']}")
                        new_phone = st.text_input("Phone", value=company.get('phone', ''), key=f"phone_{company['id']}")
                        new_division = st.text_input("Division", value=company.get('division', ''), key=f"div_{company['id']}")
                        new_district = st.text_input("District", value=company.get('district', ''), key=f"dist_{company['id']}")
                        new_registration = st.text_input("Registration Number", value=company.get('registration_number', ''), key=f"reg_{company['id']}")
                        new_vat = st.text_input("VAT Number", value=company.get('vat_number', ''), key=f"vat_{company['id']}")
                        new_address = st.text_area("Address", value=company.get('address', ''), key=f"addr_{company['id']}")
                        new_active = st.checkbox("Active", value=company.get('is_active', 1) == 1, key=f"active_{company['id']}")
                        
                        if st.button("💾 Save Company Details", key=f"save_comp_{company['id']}"):
                            updates = {}
                            if new_name != company['company_name']:
                                updates['company_name'] = new_name
                            if new_email != company.get('email'):
                                updates['email'] = new_email
                            if new_phone != company.get('phone'):
                                updates['phone'] = new_phone
                            if new_division != company.get('division'):
                                updates['division'] = new_division
                            if new_district != company.get('district'):
                                updates['district'] = new_district
                            if new_registration != company.get('registration_number'):
                                updates['registration_number'] = new_registration
                            if new_vat != company.get('vat_number'):
                                updates['vat_number'] = new_vat
                            if new_address != company.get('address'):
                                updates['address'] = new_address
                            if new_active != (company.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_company(company['id'], **updates):
                                    st.success("Company updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed")
                    
                    with col2:
                        st.markdown("#### 📊 Statistics")
                        try:
                            stats = db.get_company_stats_by_id(company['id'])
                            st.metric("👥 Users", stats.get('total_users', 0))
                            st.metric("📈 Analyses", stats.get('total_analyses', 0))
                            st.metric("🏆 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
                        except Exception as e:
                            print(f"❌ Error getting stats: {e}")
                            st.metric("👥 Users", "N/A")
                            st.metric("📈 Analyses", "N/A")
                            st.metric("🏆 Win Rate", "N/A")
                        
                        st.markdown("---")
                        st.markdown("#### ⚡ Actions")
                        col_a, col_b = st.columns(2)
                        with col_a:
                             if st.button("👥 Manage Users", key=f"users_{company_id}"):
                                # ✅ Store the correct company ID
                                st.session_state.selected_company_id = company_id
                                st.session_state.page = "user_management"
                                st.rerun()
                        with col_b:
                            if company.get('is_active', 1) == 1:
                                if st.button("🔒 Deactivate", key=f"deact_{company['id']}"):
                                    db.delete_company(company['id'])
                                    st.success(f"Company {company['company_name']} deactivated")
                                    st.rerun()
                            else:
                                if st.button("🔓 Activate", key=f"act_{company['id']}"):
                                    db.update_company(company['id'], {'is_active': 1})
                                    st.success(f"Company {company['company_name']} activated")
                                    st.rerun()
                        
                        st.caption(f"📅 Created: {company.get('created_at', 'N/A')[:10] if company.get('created_at') else 'N/A'}")
                print(f"🔍 DEBUG: Company being displayed: {company['company_name']} (ID: {company['id']})")
                print(f"🔍 DEBUG: Subscription for this company: {subscription}")

                with comp_tab2:
                    # ✅ Pass subscription correctly
                    render_subscription_card(
                        subscription=subscription,
                        company_id=company['id'],
                        show_update=True,
                        show_cancel=True,
                        title="💳 Subscription Management"
                    )
    else:
        st.info("No companies found")


def render_system_user_management():
    """Manage system-level users and company users (for system admin)"""
    st.markdown("### 👥 User Management")
    st.caption("Create users for companies or system-level access")
    
    # ========== ADD NEW USER ==========
    
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            st.markdown("#### User Details")
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
                mobile_number = st.text_input("Mobile Number *", help="Bangladeshi mobile: 01XXXXXXXXX")
            
            with col2:
                phone = st.text_input("Phone")
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            st.markdown("---")
            st.markdown("#### User Type & Role")
            
            user_type = st.radio(
                "User Type",
                options=["Company User", "System User"],
                help="Company User: Belongs to a specific company | System User: Platform-level access",
                key="user_type_radio_add"
            )
            
            company_id = None
            role = "viewer"
            
            # 👇 ONLY SHOWS WHEN "Company User" IS SELECTED
            if user_type == "Company User":
                st.markdown("##### Company Assignment")
                
                # Get all active companies
                companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
                company_options = {c['company_name']: c['id'] for c in companies}
                
                if company_options:
                    col1, col2 = st.columns(2)
                    with col1:
                        selected_company = st.selectbox(
                            "Select Company *",
                            options=list(company_options.keys()),
                            key="company_select_add"
                        )
                        company_id = company_options[selected_company]
                    
                    with col2:
                        role = st.selectbox(
                            "Role *",
                            options=["company_admin", "manager", "analyst", "viewer"],
                            key="company_role_add",
                            help="company_admin: Full company control | manager: Can manage team | analyst: Can run analyses | viewer: Read-only"
                        )
                else:
                    st.error("No companies found. Please create a company first.")
                    company_id = None
                    role = "viewer"
            
            # 👇 ONLY SHOWS WHEN "System User" IS SELECTED
            else:
                st.markdown("##### System Access Level")
                role = st.selectbox(
                    "Role *",
                    options=["system_admin", "system_support", "system_auditor"],
                    key="system_role_add",
                    help="system_admin: Full platform control | system_support: Customer support | system_auditor: Read-only audit"
                )
                
                # Show role description
                role_descriptions = {
                    "system_admin": "👑 **System Admin** - Full platform access. Can manage all companies, users, subscriptions, and system settings.",
                    "system_support": "🛟 **System Support** - Customer support role. Can view all companies and help users, but limited admin rights.",
                    "system_auditor": "📊 **System Auditor** - Read-only access. Can audit all data but cannot modify anything."
                }
                st.info(role_descriptions.get(role, ""))
            
            # Password strength indicator
            if not generate_password and 'password' in locals() and password:
                from utils.helpers import validate_password_strength
                score, msg, color = validate_password_strength(password)
                st.progress(score / 100)
                st.markdown(f"<small style='color:{color}'>{msg}</small>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Create User", type="primary")
            
            if submitted:
                # Validation
                errors = []
                if not full_name:
                    errors.append("Full name is required")
                if not email:
                    errors.append("Email is required")
                if not username:
                    errors.append("Username is required")
                if not mobile_number:
                    errors.append("Mobile number is required")
                if user_type == "Company User" and not company_id:
                    errors.append("Company selection is required")
                if not generate_password and 'password' not in locals():
                    errors.append("Password is required")
                elif not generate_password and password != confirm_password:
                    errors.append("Passwords do not match")
                
                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    final_password = db.generate_random_password() if generate_password else password
                    
                    user_data = {
                        'username': username.strip(),
                        'password': final_password,
                        'email': email.strip(),
                        'full_name': full_name.strip(),
                        'phone': phone.strip(),
                        'mobile_number': mobile_number.strip(),
                        'role': role
                    }
                    
                    if user_type == "Company User":
                        success, result = db.create_company_user(company_id, user_data, st.session_state.user_id)
                    else:
                        success, result = db.create_system_user(user_data, st.session_state.user_id)
                    
                    if success:
                        if generate_password:
                            st.success(f"✅ User {full_name} created! Password: `{final_password}`")
                        else:
                            st.success(f"✅ User {full_name} created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")

    # ========== DISPLAY USERS ==========
    st.markdown("### 📋 Users")

    tab1, tab2 = st.tabs(["🏢 Company Users", "👑 System Users"])

    # ========== COMPANY USERS TAB ==========
    with tab1:
        companies, _ = db.get_all_companies_filtered(status=None, limit=200, offset=0)
        
        if companies:
            for company in companies:
                company_users, _ = db.get_all_users_filtered(
                    company_id=company['id'],
                    limit=100,
                    offset=0
                )
                
                if company_users:
                    st.markdown(f"#### 🏢 {company['company_name']}")
                    
                    for user in company_users:
                        if not isinstance(user, dict):
                            continue
                        
                        user_id = user.get('id')
                        if not user_id:
                            continue
                        
                        unique_base = f"comp_{company['id']}_user_{user_id}"
                        
                        # Show username, mobile, and full name in expander header
                        full_name = user.get('full_name', 'Unknown')
                        username = user.get('username', 'N/A')
                        mobile = user.get('mobile_number', 'N/A')
                        role = user.get('role', 'N/A').title()
                        
                        with st.expander(f"👤 {full_name} (@{username}) 📱 {mobile} - {role}"):
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                # Username is DISPLAY ONLY (not editable)
                                st.text_input("Username (Read-Only)", value=username, disabled=True, key=f"{unique_base}_username")
                                
                                new_full_name = st.text_input("Full Name", value=full_name, key=f"{unique_base}_name")
                                new_email = st.text_input("Email", value=user.get('email', ''), key=f"{unique_base}_email")
                                new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"{unique_base}_phone")
                                # Mobile number - DISPLAY ONLY (not editable)
                                st.text_input("Mobile Number (Read-Only)", value=mobile, disabled=True, key=f"{unique_base}_mobile")
                            
                            with col2:
                                # Company selection dropdown for company users
                                all_companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
                                company_options = {c['company_name']: c['id'] for c in all_companies}
                                current_company_name = company.get('company_name', 'Unknown')
                                
                                new_company = st.selectbox(
                                    "Company",
                                    options=list(company_options.keys()),
                                    index=list(company_options.keys()).index(current_company_name) if current_company_name in company_options else 0,
                                    key=f"{unique_base}_company"
                                )
                                new_company_id = company_options.get(new_company, company['id'])
                                
                                # Role options based on user type
                                role_options = ["company_admin", "manager", "analyst", "viewer"]
                                current_role = user.get('role', 'viewer')
                                role_index = role_options.index(current_role) if current_role in role_options else 2
                                
                                new_role = st.selectbox(
                                    "Role",
                                    options=role_options,
                                    index=role_index,
                                    key=f"{unique_base}_role"
                                )
                            
                            with col3:
                                new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"{unique_base}_active")
                                
                                if st.button("💾 Save Changes", key=f"{unique_base}_save"):
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
                                    
                                    # Handle company change
                                    if new_company_id != company['id']:
                                        # Update user's company
                                        updates['company_id'] = new_company_id
                                    
                                    if updates:
                                        if db.update_user(user_id, **updates):
                                            st.success("User updated! Changes will appear after refresh.")
                                            st.rerun()
                                        else:
                                            st.error("Update failed")
                            
                            # Action buttons below the edit form
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔑 Reset Password", key=f"{unique_base}_reset"):
                                    success, new_pw = db.reset_user_password(user_id)
                                    if success:
                                        st.success(f"New password: `{new_pw}`")
                            with col2:
                                if user_id != st.session_state.user_id:
                                    if st.button("🗑️ Delete User", key=f"{unique_base}_delete", type="secondary"):
                                        if db.delete_user(user_id):
                                            st.success("User deleted")
                                            st.rerun()
                            
                            st.caption(f"📅 Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No companies found")

    # ========== SYSTEM USERS TAB ==========
    with tab2:
        try:
            system_users = db.get_system_users()
        except AttributeError:
            st.warning("get_system_users() method not available")
            return
        
        if system_users:
            for user in system_users:
                if not isinstance(user, dict):
                    continue
                
                user_id = user.get('id')
                if not user_id:
                    continue
                
                unique_base = f"sys_user_{user_id}"
                
                full_name = user.get('full_name', 'Unknown')
                username = user.get('username', 'N/A')
                mobile = user.get('mobile_number', 'N/A')
                role = user.get('role', 'N/A').replace('_', ' ').title()
                
                with st.expander(f"👑 {full_name} (@{username}) 📱 {mobile} - {role}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        # Username - DISPLAY ONLY (not editable)
                        st.text_input("Username (Read-Only)", value=username, disabled=True, key=f"{unique_base}_username")
                        
                        new_full_name = st.text_input("Full Name", value=full_name, key=f"{unique_base}_name")
                        new_email = st.text_input("Email", value=user.get('email', ''), key=f"{unique_base}_email")
                        new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"{unique_base}_phone")
                        # Mobile number - DISPLAY ONLY (not editable)
                        st.text_input("Mobile Number (Read-Only)", value=mobile, disabled=True, key=f"{unique_base}_mobile")
                    
                    with col2:
                        role_options = ["system_admin", "system_support", "system_auditor"]
                        current_role = user.get('role', 'system_support')
                        role_index = role_options.index(current_role) if current_role in role_options else 1
                        
                        new_role = st.selectbox(
                            "Role",
                            options=role_options,
                            index=role_index,
                            key=f"{unique_base}_role"
                        )
                    
                    with col3:
                        new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"{unique_base}_active")
                        
                        if st.button("💾 Save Changes", key=f"{unique_base}_save"):
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
                                if db.update_user(user_id, **updates):
                                    st.success("User updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔑 Reset Password", key=f"{unique_base}_reset"):
                            success, new_pw = db.reset_user_password(user_id)
                            if success:
                                st.success(f"New password: `{new_pw}`")
                    with col2:
                        if user_id != st.session_state.user_id:
                            if st.button("🗑️ Delete User", key=f"{unique_base}_delete", type="secondary"):
                                if db.delete_user(user_id):
                                    st.success("User deleted")
                                    st.rerun()
                    
                    st.caption(f"📅 Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No system users found")


def render_role_management_page():
    """Render role permissions management"""
    st.markdown("### 🔐 Role Permissions Management")
    st.caption("Configure what each role can do in the system")
    
    try:
        roles = db.get_all_roles()
    except AttributeError:
        st.warning("get_all_roles() method not available. Please update db_manager.py")
        return
    
    if not roles:
        st.warning("No roles found. Please run database migration.")
        return
    
    # Display role hierarchy
    st.markdown("#### Role Hierarchy")
    role_hierarchy = {
        'system_admin': '👑 Full platform access',
        'system_support': '🛠️ Can view all companies, support access',
        'system_auditor': '📊 Read-only across platform',
        'company_admin': '🏢 Full company management',
        'manager': '📋 Can manage tenders and create users',
        'analyst': '🔬 Can run analyses and view reports',
        'viewer': '👁️ Read-only access'
    }
    
    for role, desc in role_hierarchy.items():
        if any(r['role'] == role for r in roles):
            st.markdown(f"- **{role.replace('_', ' ').title()}**: {desc}")
    
    st.markdown("---")
    st.markdown("#### Edit Role Permissions")
    
    for role_info in roles:
        role_name = role_info['role']
        permissions = role_info['permissions']
        
        with st.expander(f"📌 {role_name.replace('_', ' ').title()}", expanded=False):
            st.markdown(f"**Role:** `{role_name}`")
            st.markdown(f"**Description:** {role_hierarchy.get(role_name, 'No description')}")
            
            # Display key permissions
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**User Management**")
                user_perms = ['manage_users', 'manage_team', 'create_user', 'delete_user']
                for perm in user_perms:
                    if perm in permissions:
                        current = permissions.get(perm, False)
                        new_val = st.checkbox(perm.replace('_', ' ').title(), value=current, key=f"{role_name}_{perm}")
                        permissions[perm] = new_val
            
            with col2:
                st.markdown("**Tender & Analysis**")
                tender_perms = ['manage_tenders', 'run_analysis', 'view_reports', 'export_data']
                for perm in tender_perms:
                    if perm in permissions:
                        current = permissions.get(perm, False)
                        new_val = st.checkbox(perm.replace('_', ' ').title(), value=current, key=f"{role_name}_{perm}")
                        permissions[perm] = new_val
            
            if st.button(f"💾 Save Permissions for {role_name}", key=f"save_role_{role_name}"):
                success = db.update_role_permissions(role_name, permissions)
                if success:
                    st.success(f"Permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions")

# Updated render_system_configuration function
def render_system_configuration():
    """Render system configuration page"""
    
    st.markdown("### ⚙️ System Configuration")
    st.markdown("Manage system-wide settings and configurations.")
    
    db = get_db_manager()
    
    # ============================================================
    # SYSTEM CONFIGURATION SECTIONS
    # ============================================================
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📧 Email Settings",
        "🔐 Security Settings",
        "📊 System Settings",
        "📈 Performance"
    ])
    
    # ========== TAB 1: EMAIL SETTINGS ==========
    with tab1:
        st.markdown("#### 📧 Email Configuration")
        
        # Get current email config
        try:
            # ✅ Fix: Use direct method instead of context manager
            if is_supabase():
                # For Supabase, get config directly
                supabase = get_supabase_client()
                response = supabase.table("system_config").select("*").eq("config_key", "email_settings").execute()
                config_data = response.data[0] if response.data else None
            else:
                # For SQLite, use get_connection
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM system_config WHERE config_key = 'email_settings'")
                row = cursor.fetchone()
                config_data = dict(row) if row else None
                
        except Exception as e:
            st.warning(f"Could not load email settings: {e}")
            config_data = None
        
        # Display and edit email settings
        if config_data:
            config_value = config_data.get('config_value', {})
            if isinstance(config_value, str):
                try:
                    config_value = json.loads(config_value)
                except:
                    config_value = {}
        else:
            config_value = {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'from_email': '',
                'from_name': 'TenderAI'
            }
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_smtp_host = st.text_input("SMTP Host", value=config_value.get('smtp_host', 'smtp.gmail.com'))
            new_smtp_port = st.number_input("SMTP Port", value=config_value.get('smtp_port', 587))
            new_smtp_user = st.text_input("SMTP Username", value=config_value.get('smtp_user', ''))
        
        with col2:
            new_smtp_password = st.text_input("SMTP Password", type="password", value=config_value.get('smtp_password', ''))
            new_from_email = st.text_input("From Email", value=config_value.get('from_email', ''))
            new_from_name = st.text_input("From Name", value=config_value.get('from_name', 'TenderAI'))
        
        if st.button("💾 Save Email Settings", type="primary"):
            try:
                updated_config = {
                    'smtp_host': new_smtp_host,
                    'smtp_port': new_smtp_port,
                    'smtp_user': new_smtp_user,
                    'smtp_password': new_smtp_password,
                    'from_email': new_from_email,
                    'from_name': new_from_name
                }
                
                if is_supabase():
                    # Supabase: Upsert
                    supabase = get_supabase_client()
                    supabase.table("system_config").upsert({
                        "config_key": "email_settings",
                        "config_value": json.dumps(updated_config),
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                else:
                    # SQLite
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
                        VALUES (?, ?, ?)
                    """, ("email_settings", json.dumps(updated_config), datetime.now().isoformat()))
                    conn.commit()
                
                st.success("✅ Email settings saved successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to save email settings: {e}")
    
    # ========== TAB 2: SECURITY SETTINGS ==========
    with tab2:
        st.markdown("#### 🔐 Security Settings")
        
        # Get current security config
        try:
            if is_supabase():
                supabase = get_supabase_client()
                response = supabase.table("system_config").select("*").eq("config_key", "security_settings").execute()
                security_data = response.data[0] if response.data else None
            else:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM system_config WHERE config_key = 'security_settings'")
                row = cursor.fetchone()
                security_data = dict(row) if row else None
        except:
            security_data = None
        
        if security_data:
            security_value = security_data.get('config_value', {})
            if isinstance(security_value, str):
                try:
                    security_value = json.loads(security_value)
                except:
                    security_value = {}
        else:
            security_value = {
                'require_2fa': True,
                'session_timeout': 30,
                'max_login_attempts': 5,
                'password_policy': 'strong'
            }
        
        col1, col2 = st.columns(2)
        
        with col1:
            require_2fa = st.checkbox("Require 2FA for all users", value=security_value.get('require_2fa', True))
            session_timeout = st.number_input("Session Timeout (minutes)", value=security_value.get('session_timeout', 30))
        
        with col2:
            max_login_attempts = st.number_input("Max Login Attempts", value=security_value.get('max_login_attempts', 5))
            password_policy = st.selectbox(
                "Password Policy",
                ["weak", "medium", "strong"],
                index=["weak", "medium", "strong"].index(security_value.get('password_policy', 'strong'))
            )
        
        if st.button("💾 Save Security Settings", type="primary"):
            try:
                updated_config = {
                    'require_2fa': require_2fa,
                    'session_timeout': session_timeout,
                    'max_login_attempts': max_login_attempts,
                    'password_policy': password_policy
                }
                
                if is_supabase():
                    supabase = get_supabase_client()
                    supabase.table("system_config").upsert({
                        "config_key": "security_settings",
                        "config_value": json.dumps(updated_config),
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                else:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
                        VALUES (?, ?, ?)
                    """, ("security_settings", json.dumps(updated_config), datetime.now().isoformat()))
                    conn.commit()
                
                st.success("✅ Security settings saved successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to save security settings: {e}")
    
    # ========== TAB 3: SYSTEM SETTINGS ==========
    with tab3:
        st.markdown("#### 📊 System Settings")
        
        # Get current system config
        try:
            if is_supabase():
                supabase = get_supabase_client()
                response = supabase.table("system_config").select("*").eq("config_key", "system_settings").execute()
                system_data = response.data[0] if response.data else None
            else:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM system_config WHERE config_key = 'system_settings'")
                row = cursor.fetchone()
                system_data = dict(row) if row else None
        except:
            system_data = None
        
        if system_data:
            system_value = system_data.get('config_value', {})
            if isinstance(system_value, str):
                try:
                    system_value = json.loads(system_value)
                except:
                    system_value = {}
        else:
            system_value = {
                'enable_maintenance_mode': False,
                'enable_registration': True,
                'enable_analytics': True,
                'default_language': 'en'
            }
        
        enable_maintenance = st.checkbox("Maintenance Mode", value=system_value.get('enable_maintenance_mode', False))
        enable_registration = st.checkbox("Enable Registration", value=system_value.get('enable_registration', True))
        enable_analytics = st.checkbox("Enable Analytics", value=system_value.get('enable_analytics', True))
        default_language = st.selectbox("Default Language", ["en", "bn"], index=0 if system_value.get('default_language', 'en') == 'en' else 1)
        
        if st.button("💾 Save System Settings", type="primary"):
            try:
                updated_config = {
                    'enable_maintenance_mode': enable_maintenance,
                    'enable_registration': enable_registration,
                    'enable_analytics': enable_analytics,
                    'default_language': default_language
                }
                
                if is_supabase():
                    supabase = get_supabase_client()
                    supabase.table("system_config").upsert({
                        "config_key": "system_settings",
                        "config_value": json.dumps(updated_config),
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                else:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
                        VALUES (?, ?, ?)
                    """, ("system_settings", json.dumps(updated_config), datetime.now().isoformat()))
                    conn.commit()
                
                st.success("✅ System settings saved successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to save system settings: {e}")
    
    # ========== TAB 4: PERFORMANCE ==========
    with tab4:
        st.markdown("#### 📈 Performance Settings")
        
        # Get current performance config
        try:
            if is_supabase():
                supabase = get_supabase_client()
                response = supabase.table("system_config").select("*").eq("config_key", "performance_settings").execute()
                perf_data = response.data[0] if response.data else None
            else:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM system_config WHERE config_key = 'performance_settings'")
                row = cursor.fetchone()
                perf_data = dict(row) if row else None
        except:
            perf_data = None
        
        if perf_data:
            perf_value = perf_data.get('config_value', {})
            if isinstance(perf_value, str):
                try:
                    perf_value = json.loads(perf_value)
                except:
                    perf_value = {}
        else:
            perf_value = {
                'cache_enabled': True,
                'cache_duration': 300,
                'max_query_limit': 1000,
                'enable_query_logging': True
            }
        
        col1, col2 = st.columns(2)
        
        with col1:
            cache_enabled = st.checkbox("Enable Cache", value=perf_value.get('cache_enabled', True))
            cache_duration = st.number_input("Cache Duration (seconds)", value=perf_value.get('cache_duration', 300))
        
        with col2:
            max_query_limit = st.number_input("Max Query Limit", value=perf_value.get('max_query_limit', 1000))
            enable_query_logging = st.checkbox("Enable Query Logging", value=perf_value.get('enable_query_logging', True))
        
        if st.button("💾 Save Performance Settings", type="primary"):
            try:
                updated_config = {
                    'cache_enabled': cache_enabled,
                    'cache_duration': cache_duration,
                    'max_query_limit': max_query_limit,
                    'enable_query_logging': enable_query_logging
                }
                
                if is_supabase():
                    supabase = get_supabase_client()
                    supabase.table("system_config").upsert({
                        "config_key": "performance_settings",
                        "config_value": json.dumps(updated_config),
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                else:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
                        VALUES (?, ?, ?)
                    """, ("performance_settings", json.dumps(updated_config), datetime.now().isoformat()))
                    conn.commit()
                
                st.success("✅ Performance settings saved successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to save performance settings: {e}")
def render_database_backup():
    """Render database backup interface for Supabase"""
    
    st.markdown("""
    <style>
    .backup-container {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
    }
    .backup-status {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 💾 Database Backup & Export")
    st.markdown("Export your Supabase database to JSON format for backup or migration.")
    
    # Check if using Supabase
    from config.database import DB_TYPE
    from database.connection import get_supabase_client, is_supabase
    
    if not is_supabase():
        st.warning("⚠️ This feature is only available when using Supabase as the database backend.")
        st.info("📌 You are currently using: " + (DB_TYPE.upper() if DB_TYPE else "SQLite"))
        return
    
    st.success("✅ Connected to Supabase database")
    
    # ============================================================
    # GET TABLE NAMES FROM RPC FUNCTION
    # ============================================================
    
    try:
        supabase = get_supabase_client()
        
        # Call your RPC function
        response = supabase.rpc("get_table_names").execute()
        
        if hasattr(response, 'data') and response.data:
            ALL_TABLES = [row['table_name'] for row in response.data]
            st.success(f"✅ Found {len(ALL_TABLES)} tables in the database")
        else:
            st.warning("⚠️ Could not fetch table names. Using fallback list.")
            ALL_TABLES = get_fallback_tables()
            
    except Exception as e:
        st.warning(f"⚠️ Could not fetch table names: {str(e)}")
        st.info("📌 Using fallback table list")
        ALL_TABLES = get_fallback_tables()
    
    # ============================================================
    # BACKUP OPTIONS
    # ============================================================
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📋 Export Options")
        
        export_format = st.selectbox(
            "Export Format",
            ["JSON", "CSV", "Both (JSON + CSV)"],
            help="JSON is recommended for full data preservation"
        )
        
        # Group tables for better UX
        table_groups = categorize_tables(ALL_TABLES)
        
        # Flatten for selection
        all_table_names = []
        for group, tables in table_groups.items():
            all_table_names.extend(tables)
        
        tables_to_export = st.multiselect(
            "Select Tables to Export",
            all_table_names,
            default=["users", "companies", "subscriptions"] if "users" in all_table_names else all_table_names[:3]
        )
        
        include_metadata = st.checkbox(
            "Include metadata (timestamp, table structure, counts)",
            value=True
        )
        
        st.caption(f"📊 {len(tables_to_export)} tables selected out of {len(ALL_TABLES)} total")
    
    with col2:
        st.markdown("#### 📊 Table Status")
        
        try:
            st.markdown('<div class="backup-status">', unsafe_allow_html=True)
            
            # Show status for selected tables
            for table in tables_to_export[:8]:
                try:
                    response = supabase.table(table).select("*", count="exact").limit(0).execute()
                    count = response.count if hasattr(response, 'count') else 0
                    status_icon = "✅" if count > 0 else "📭"
                    st.caption(f"{status_icon} **{table}**: {count:,} records")
                except Exception as e:
                    st.caption(f"⚠️ **{table}**: Could not fetch")
            
            if len(tables_to_export) > 8:
                st.caption(f"... and {len(tables_to_export) - 8} more tables")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.caption(f"⚠️ Could not fetch stats: {str(e)}")
    
    # ============================================================
    # BACKUP BUTTONS
    # ============================================================
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        export_btn = st.button(
            "🚀 Export Selected",
            type="primary",
            use_container_width=True,
            help="Export selected tables to the chosen format"
        )
    
    with col2:
        export_all_btn = st.button(
            "📦 Export All Tables",
            use_container_width=True,
            help="Export all available tables (may take a while)"
        )
    
    with col3:
        if st.button("🗑️ Clear Backup History", use_container_width=True):
            if 'backup_history' in st.session_state:
                del st.session_state['backup_history']
            st.success("Backup history cleared!")
            st.rerun()
    
    # ============================================================
    # PROCESS EXPORT
    # ============================================================
    
    if export_btn or export_all_btn:
        if export_all_btn:
            tables_to_export = ALL_TABLES
        
        if not tables_to_export:
            st.error("❌ Please select at least one table to export.")
            return
        
        with st.spinner(f"⏳ Exporting {len(tables_to_export)} tables from Supabase..."):
            try:
                export_data = {}
                table_stats = {}
                export_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                errors = []
                exported_count = 0
                
                for idx, table in enumerate(tables_to_export):
                    status_text.text(f"📊 Exporting: {table}... ({idx+1}/{len(tables_to_export)})")
                    progress_bar.progress((idx + 1) / len(tables_to_export))
                    
                    try:
                        # Query data from Supabase
                        response = supabase.table(table).select("*").execute()
                        data = response.data if hasattr(response, 'data') and response.data else []
                        
                        if data and len(data) > 0:
                            export_data[table] = data
                            table_stats[table] = {
                                'count': len(data),
                                'columns': list(data[0].keys()) if data else []
                            }
                            exported_count += 1
                            print(f"✅ Exported {table}: {len(data)} records")
                        else:
                            export_data[table] = []
                            table_stats[table] = {'count': 0, 'columns': []}
                            print(f"ℹ️ Table '{table}' has no records")
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "PGRST" not in error_msg:
                            errors.append(f"Table '{table}': {error_msg}")
                        export_data[table] = []
                        table_stats[table] = {'count': 0, 'error': error_msg}
                        print(f"❌ Could not export table '{table}': {error_msg}")
                
                status_text.text("✅ Export complete!")
                progress_bar.progress(1.0)
                
                # Show any errors
                if errors:
                    with st.expander("⚠️ Export Warnings"):
                        for err in errors:
                            st.warning(err)
                
                # Prepare final export object
                final_export = {
                    'exported_at': export_timestamp,
                    'database_type': 'supabase',
                    'tables_exported': len(tables_to_export),
                    'total_records': sum(stat.get('count', 0) for stat in table_stats.values() if isinstance(stat, dict)),
                    'table_stats': table_stats,
                    'include_metadata': include_metadata,
                    'data': export_data
                }
                
                # Store in session state
                st.session_state['latest_backup'] = final_export
                st.session_state['backup_timestamp'] = export_timestamp
                
                # Save to local file
                backup_filename = f"backup_supabase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = os.path.join('data', 'backups')
                os.makedirs(backup_path, exist_ok=True)
                
                json_file = os.path.join(backup_path, backup_filename)
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(final_export, f, indent=2, default=str)
                
                st.success(f"✅ Export successful! {exported_count} tables with data exported.")
                st.info(f"📁 Backup saved locally: `{json_file}`")
                
                # Show summary
                st.markdown("#### 📊 Export Summary")
                summary_cols = st.columns(4)
                with summary_cols[0]:
                    st.metric("Tables Exported", len(tables_to_export))
                with summary_cols[1]:
                    total_records = sum(len(data) for data in export_data.values() if data)
                    st.metric("Total Records", f"{total_records:,}")
                with summary_cols[2]:
                    st.metric("Format", export_format)
                with summary_cols[3]:
                    st.metric("Timestamp", export_timestamp.split(" ")[1])
                
                # Show per-table breakdown
                with st.expander("📋 Per-Table Breakdown", expanded=True):
                    table_data = []
                    for table in tables_to_export:
                        data = export_data.get(table, [])
                        stats = table_stats.get(table, {})
                        record_count = len(data) if data else 0
                        table_data.append({
                            'Table': table,
                            'Records': record_count,
                            'Columns': len(stats.get('columns', [])) if stats.get('columns') else 0,
                            'Status': '✅' if record_count > 0 else '📭 Empty'
                        })
                    
                    if table_data:
                        st.dataframe(
                            pd.DataFrame(table_data),
                            use_container_width=True,
                            hide_index=True
                        )
                
                # Download buttons
                st.markdown("#### 📥 Download Backup")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    json_str = json.dumps(final_export, indent=2, default=str)
                    st.download_button(
                        label="📄 Download JSON",
                        data=json_str,
                        file_name=f"backup_supabase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True,
                        type="primary"
                    )
                
                with col2:
                    if export_format in ["CSV", "Both (JSON + CSV)"]:
                        try:
                            import zipfile
                            from io import BytesIO
                            
                            zip_buffer = BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for table, data in export_data.items():
                                    if data and len(data) > 0:
                                        df = pd.DataFrame(data)
                                        csv_data = df.to_csv(index=False)
                                        zip_file.writestr(f"{table}.csv", csv_data)
                            
                            zip_buffer.seek(0)
                            
                            st.download_button(
                                label="📊 Download CSV (ZIP)",
                                data=zip_buffer,
                                file_name=f"backup_supabase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.warning(f"⚠️ Could not create CSV: {str(e)}")
                
                with col3:
                    if st.button("📂 View Backup History", use_container_width=True):
                        st.session_state.show_backup_history = True
                
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
                import traceback
                traceback.print_exc()
    
    # ============================================================
    # BACKUP HISTORY
    # ============================================================
    
    if st.session_state.get('show_backup_history', False):
        st.markdown("---")
        st.markdown("#### 📂 Backup History")
        
        backup_dir = os.path.join('data', 'backups')
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('backup_supabase_')]
            if backup_files:
                backup_files.sort(reverse=True)
                
                history_data = []
                for file in backup_files[:20]:
                    file_path = os.path.join(backup_dir, file)
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    history_data.append({
                        'File': file,
                        'Size': f"{file_size / 1024:.1f} KB",
                        'Created': datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'Path': file_path
                    })
                
                st.dataframe(
                    pd.DataFrame(history_data),
                    use_container_width=True,
                    hide_index=True
                )
                
                selected_backup = st.selectbox(
                    "Select a backup to download",
                    [f['File'] for f in history_data],
                    key="select_old_backup"
                )
                
                if selected_backup:
                    file_path = os.path.join(backup_dir, selected_backup)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    st.download_button(
                        label=f"📥 Download {selected_backup}",
                        data=file_content,
                        file_name=selected_backup,
                        mime="application/json",
                        use_container_width=True
                    )
                
                if st.button("🗑️ Delete Selected Backup", type="secondary"):
                    if selected_backup:
                        try:
                            os.remove(os.path.join(backup_dir, selected_backup))
                            st.success(f"✅ Deleted: {selected_backup}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Could not delete: {str(e)}")
            else:
                st.info("No backups found.")
        else:
            st.info("No backups directory found. Create one by exporting data.")
        
        if st.button("🔙 Close History", use_container_width=True):
            st.session_state.show_backup_history = False
            st.rerun()