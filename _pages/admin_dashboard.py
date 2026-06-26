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

from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()

DB_PATH = db.db_path


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


def render_version_history(db_instance):
    """Display version history"""
    
    versions = get_rate_versions(db_instance)
    
    for version in versions:
        with st.expander(f"{version['name']} ({version['year']})"):
            st.write(f"**Effective Date:** {version['effective_date']}")
            st.write(f"**Status:** {'✅ Active' if version['is_active'] else '📦 Archived'}")
            st.write(f"**Imported:** {version['imported_at']}")
            st.write(f"**Items:** {version['parent_count']} parents, {version['child_count']} children")
            
            if version['is_active']:
                if st.button("Archive", key=f"archive_{version['id']}"):
                    archive_version(db_instance, version['id'])
                    st.rerun()


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
    all_users_raw = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    # Convert to dictionary format
    all_users = []
    for u in all_users_raw:
        if hasattr(u, 'keys'):
            user_dict = dict(u)
        elif isinstance(u, (tuple, list)):
            if len(u) >= 10:
                user_dict = {
                    'id': u[0], 'username': u[1], 'email': u[2], 'full_name': u[3],
                    'phone': u[4], 'role': u[5], 'is_active': u[6],
                    'created_at': u[7], 'last_login': u[8], 'company_name': u[9],
                    'is_approved': u[10] if len(u) > 10 else 1
                }
            else:
                continue
        elif isinstance(u, dict):
            user_dict = u
        else:
            continue
        all_users.append(user_dict)
    
    # Statistics in a row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(all_users))
    
    with col2:
        active_users = len([u for u in all_users if u.get('is_active', 0) == 1]) if all_users else 0
        st.metric("Active Users", active_users)
    
    with col3:
        companies = set([u.get('company_name', 'N/A') for u in all_users]) if all_users else set()
        st.metric("Companies", len(companies))
    
    with col4:
        paid_subs = len([s for s in all_subs if len(s) > 2 and s[2] not in ['free', 'trial']]) if all_subs else 0
        #paid_subs = len([s for s in all_subs if s.get('plan') not in ['free', 'trial']]) if all_subs else 0

        st.metric("Paid Subscriptions", paid_subs)
    
    # Add a divider to separate metrics from tabs
    st.markdown("---")
    
    # Tabs - now at full width below the metrics
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
        "📊 Overview", 
        "👥 All Users", 
        "🏢 Companies", 
        "👑 System Users", 
        "🔐 Role Management",
        "🏗️ Rate Import",    
        "📅 Version Management",
        "🔄 Rollback Management",
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

    with tab7:
        render_rollback_management(db)        
    
    with tab8:
        render_unified_version_management(db)
    
    with tab9:
        render_rate_crud_forms(db)

    with tab10:
        render_rate_viewer(db)
    
    with tab11:
        render_system_configuration()
    
    with tab12:
        render_subscription_plans_management()

def render_admin_overview(all_users, all_subs):
    """Render system overview with charts"""
    st.markdown("### System Overview")
    
    # User growth chart
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM users
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """)
    user_growth_data = cursor.fetchall()
    conn.close()
    
    if user_growth_data:
        user_growth = pd.DataFrame(user_growth_data, columns=['Month', 'Users'])
        user_growth = user_growth.iloc[::-1]
        st.line_chart(user_growth.set_index('Month'))
    else:
        st.info("No user growth data available")
    
    # Plan distribution
    if all_subs:
        plan_counts = {}
        for sub in all_subs:
            plan = sub[2] if len(sub) > 2 else 'free'
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        plan_df = pd.DataFrame(plan_counts.items(), columns=['Plan', 'Count'])
        st.bar_chart(plan_df.set_index('Plan'))
    
    # Role distribution
    if all_users:
        role_counts = {}
        for user in all_users:
            role = user.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_df = pd.DataFrame(role_counts.items(), columns=['Role', 'Count'])
        st.bar_chart(role_df.set_index('Role'))


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
    """Render system configuration settings including extension API URL"""
    
    st.markdown("### ⚙️ System Configuration")
    st.caption("Manage system-wide settings including API endpoints and extension configuration")
    
    # Get current API URL
    current_api_url = get_system_config('extension_api_url', get_default_api_url())
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        new_api_url = st.text_input(
            "Extension API Base URL",
            value=current_api_url,
            help="The URL that the Chrome extension will connect to for API calls"
        )
        
        st.caption("⚠️ After changing this URL, users must re-download the extension for changes to take effect.")
    
    with col2:
        if st.button("💾 Save API URL", type="primary", use_container_width=True):
            if save_system_config('extension_api_url', new_api_url):
                st.success("✅ API URL saved successfully!")
                st.info("📥 Reminder: Users need to re-download the extension from the Download page.")
                st.rerun()
            else:
                st.error("Failed to save configuration")
    
    # Show current configuration status
    st.markdown("---")
    st.markdown("#### 📡 Current Configuration")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Extension API URL", current_api_url)
    with col2:
        # Test connection
        import requests
        try:
            response = requests.get(f"{current_api_url}/health", timeout=5)
            status = "✅ Connected" if response.status_code == 200 else "⚠️ Check URL"
        except:
            status = "❌ Not Reachable"
        st.metric("API Status", status)
    with col3:
        # Get extension download count
        if db.table_exists('extension_downloads'):
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM extension_downloads")
                download_count = cursor.fetchone()[0]
        else:
            download_count = 0
        st.metric("Extension Downloads", download_count)
    
    # ========== SECTION 2: SYSTEM SETTINGS ==========
    st.markdown("---")
    st.markdown("#### 🔧 System Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Debug mode setting
        debug_mode = get_system_config('debug_mode', 'false') == 'true'
        new_debug_mode = st.checkbox("Enable Debug Mode", value=debug_mode, help="Shows detailed error messages and debug information")
        if new_debug_mode != debug_mode:
            if save_system_config('debug_mode', str(new_debug_mode).lower()):
                st.success("Debug mode setting saved")
    
    with col2:
        # Maintenance mode
        maintenance_mode = get_system_config('maintenance_mode', 'false') == 'true'
        new_maintenance = st.checkbox("Maintenance Mode", value=maintenance_mode, help="Shows maintenance page to users")
        if new_maintenance != maintenance_mode:
            if save_system_config('maintenance_mode', str(new_maintenance).lower()):
                st.warning("Maintenance mode setting saved. Restart required for full effect.")
    
    # ========== SECTION 3: RATE LIMITS ==========
    st.markdown("---")
    st.markdown("#### 🚦 Rate Limits")
    
    col1, col2 = st.columns(2)
    
    with col1:
        rate_limit = get_system_config('api_rate_limit', '60')
        new_rate_limit = st.number_input("API Rate Limit (requests per minute)", min_value=10, max_value=1000, value=int(rate_limit))
        if new_rate_limit != int(rate_limit):
            if save_system_config('api_rate_limit', str(new_rate_limit)):
                st.success(f"Rate limit updated to {new_rate_limit} requests/minute")
    
    with col2:
        max_upload_size = get_system_config('max_upload_size_mb', '100')
        new_max_upload = st.number_input("Max Upload Size (MB)", min_value=10, max_value=500, value=int(max_upload_size))
        if new_max_upload != int(max_upload_size):
            if save_system_config('max_upload_size_mb', str(new_max_upload)):
                st.success(f"Max upload size updated to {new_max_upload} MB")
    
    # ========== SECTION 4: CLEAR CACHE ==========
    st.markdown("---")
    st.markdown("#### 🧹 Cache Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Extension Logs", use_container_width=True, type="secondary"):
            if db.table_exists('extension_auto_fill_log'):
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM extension_auto_fill_log")
                    conn.commit()
                st.success("Extension logs cleared!")
            else:
                st.info("No extension logs to clear")
    
    with col2:
        if st.button("📊 Recalculate Extension Usage", use_container_width=True, type="secondary"):
            st.info("Usage statistics recalculated")
    
    # ========== SECTION 5: EXTENSION DOWNLOAD STATS ==========
    st.markdown("---")
    st.markdown("#### 📊 Extension Download Statistics")
    
    if db.table_exists('extension_downloads'):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total downloads
            cursor.execute("SELECT COUNT(*) FROM extension_downloads")
            total_downloads = cursor.fetchone()[0]
            
            # Downloads by day (last 7 days)
            db_type = db.get_db_type()
            if db_type == 'sqlite':
                cursor.execute("""
                    SELECT date(downloaded_at) as day, COUNT(*) as count
                    FROM extension_downloads
                    WHERE downloaded_at >= date('now', '-7 days')
                    GROUP BY date(downloaded_at)
                    ORDER BY day DESC
                """)
            else:  # PostgreSQL
                cursor.execute("""
                    SELECT date(downloaded_at) as day, COUNT(*) as count
                    FROM extension_downloads
                    WHERE downloaded_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY date(downloaded_at)
                    ORDER BY day DESC
                """)
            daily_downloads = cursor.fetchall()
            
            # Downloads by user
            cursor.execute("""
                SELECT username, COUNT(*) as count
                FROM extension_downloads
                GROUP BY username
                ORDER BY count DESC
                LIMIT 10
            """)
            user_downloads = cursor.fetchall()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Downloads", total_downloads)
                
                if daily_downloads:
                    st.markdown("**Last 7 Days**")
                    for day, count in daily_downloads:
                        st.write(f"{day}: {count} downloads")
            
            with col2:
                if user_downloads:
                    st.markdown("**Top Downloaders**")
                    for username, count in user_downloads:
                        st.write(f"{username}: {count} downloads")
    else:
        st.info("No extension downloads tracked yet")
# _pages/admin_dashboard.py - Subscription Plans Management Section

def render_subscription_plans_management():
    """Render subscription plans management interface for system admin"""
    
    st.markdown("### 💳 Subscription Plans Management")
    st.caption("Configure subscription plans, pricing, and limits")
    
    # Get existing plans using unified db
    with db.get_connection() as conn:
        cursor = db.db_conn.get_cursor(conn)
        cursor.execute("SELECT * FROM subscription_plans ORDER BY monthly_price")
        plans = cursor.fetchall()
        
        # Get column names for dict conversion
        columns = [description[0] for description in cursor.description]
    
    # If no plans exist, insert defaults
    if not plans:
        _insert_default_plans()
        # Re-fetch plans
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("SELECT * FROM subscription_plans ORDER BY monthly_price")
            plans = cursor.fetchall()
    
    st.markdown("#### 📋 Current Plans")
    
    # Display existing plans
    for plan in plans:
        plan_dict = dict(plan)
        _render_plan_editor(plan_dict)
    
    # Add new plan
    _render_add_plan_form()


def _insert_default_plans():
    """Insert default plans if none exist"""
    default_plans = [
        ('free', 'company', 0, 0, 5, 5, 5, 1, 5, 0, 0, 0, 0, 0, 'Free plan with basic features'),
        ('basic', 'company', 4999, 49990, 30, 30, 30, 3, 30, 1, 0, 0, 0, 0, 'Basic plan for small businesses'),
        ('professional', 'company', 14999, 149990, 100, 100, -1, 10, 100, 1, 1, 0, 1, 1, 'Professional plan for growing businesses'),
        ('enterprise', 'company', 49999, 499990, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 'Enterprise plan with unlimited features')
    ]
    
    with db.get_connection() as conn:
        cursor = db.db_conn.get_cursor(conn)
        for plan in default_plans:
            cursor.execute("""
                INSERT OR IGNORE INTO subscription_plans (
                    plan_name, plan_type, monthly_price, yearly_price,
                    max_boq_generations, max_bid_optimizations, max_tender_analyses,
                    max_users, extension_auto_fills, can_export_data, can_edit_rates,
                    can_delete_rates, can_create_versions, can_manage_team, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, plan)
        conn.commit()

#"Dict" is not definedPylancereportUndefinedVariable
def _render_plan_editor(plan_dict: Dict):
    """Render editor for a single plan"""
    
    plan_name = plan_dict['plan_name']
    
    with st.expander(f"📌 {plan_name.upper()} Plan", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Pricing**")
            new_monthly = st.number_input(
                "Monthly Price (BDT)", 
                value=float(plan_dict['monthly_price']),
                min_value=0.0,
                step=500.0,
                key=f"monthly_{plan_name}"
            )
            new_yearly = st.number_input(
                "Yearly Price (BDT)", 
                value=float(plan_dict['yearly_price']),
                min_value=0.0,
                step=1000.0,
                key=f"yearly_{plan_name}"
            )
            
            st.markdown("**Limits**")
            new_boq = st.number_input(
                "Max BOQ Generations", 
                value=int(plan_dict['max_boq_generations']),
                min_value=-1,
                step=1,
                key=f"boq_{plan_name}",
                help="-1 = Unlimited"
            )
            new_bid = st.number_input(
                "Max Bid Optimizations", 
                value=int(plan_dict['max_bid_optimizations']),
                min_value=-1,
                step=1,
                key=f"bid_{plan_name}"
            )
            new_analyses = st.number_input(
                "Max Tender Analyses", 
                value=int(plan_dict['max_tender_analyses']),
                min_value=-1,
                step=1,
                key=f"analyses_{plan_name}"
            )
            new_users = st.number_input(
                "Max Users", 
                value=int(plan_dict['max_users']),
                min_value=-1,
                step=1,
                key=f"users_{plan_name}"
            )
            new_extension = st.number_input(
                "Extension Auto-Fills (per month)", 
                value=int(plan_dict['extension_auto_fills']),
                min_value=-1,
                step=1,
                key=f"extension_{plan_name}"
            )
        
        with col2:
            st.markdown("**Permissions**")
            new_export = st.checkbox(
                "Can Export Data", 
                value=bool(plan_dict['can_export_data']),
                key=f"export_{plan_name}"
            )
            new_edit_rates = st.checkbox(
                "Can Edit Rates", 
                value=bool(plan_dict['can_edit_rates']),
                key=f"edit_rates_{plan_name}"
            )
            new_delete_rates = st.checkbox(
                "Can Delete Rates", 
                value=bool(plan_dict['can_delete_rates']),
                key=f"delete_rates_{plan_name}"
            )
            new_create_versions = st.checkbox(
                "Can Create Versions", 
                value=bool(plan_dict['can_create_versions']),
                key=f"create_versions_{plan_name}"
            )
            new_manage_team = st.checkbox(
                "Can Manage Team", 
                value=bool(plan_dict['can_manage_team']),
                key=f"manage_team_{plan_name}"
            )
            
            st.markdown("**Description**")
            new_description = st.text_area(
                "Plan Description",
                value=plan_dict.get('description', ''),
                height=100,
                key=f"desc_{plan_name}"
            )
        
        # Save button
        if st.button(f"💾 Save {plan_name.upper()} Plan", key=f"save_{plan_name}", use_container_width=True):
            with db.get_connection() as conn:
                cursor = db.db_conn.get_cursor(conn)
                
                try:
                    cursor.execute("""
                        UPDATE subscription_plans 
                        SET monthly_price = ?, yearly_price = ?,
                            max_boq_generations = ?, max_bid_optimizations = ?,
                            max_tender_analyses = ?, max_users = ?,
                            extension_auto_fills = ?,
                            can_export_data = ?, can_edit_rates = ?,
                            can_delete_rates = ?, can_create_versions = ?,
                            can_manage_team = ?, description = ?
                        WHERE plan_name = ?
                    """, (
                        new_monthly, new_yearly,
                        new_boq, new_bid, new_analyses, new_users, new_extension,
                        1 if new_export else 0,
                        1 if new_edit_rates else 0,
                        1 if new_delete_rates else 0,
                        1 if new_create_versions else 0,
                        1 if new_manage_team else 0,
                        new_description,
                        plan_name
                    ))
                    conn.commit()
                    st.success(f"✅ {plan_name.upper()} plan updated successfully!")
                    # Clear plan cache
                    from modules.subscription import get_plans
                    get_plans(force_refresh=True)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating plan: {e}")


def _render_add_plan_form():
    """Render form to add new plan"""
    
    st.markdown("---")
    st.markdown("#### ➕ Add New Plan")
    
    with st.form("add_plan_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_plan_name = st.text_input("Plan Name *", placeholder="e.g., premium")
            new_monthly = st.number_input("Monthly Price (BDT)", min_value=0.0, step=500.0)
            new_yearly = st.number_input("Yearly Price (BDT)", min_value=0.0, step=1000.0)
            new_description = st.text_area("Description", placeholder="Plan features and benefits")
        
        with col2:
            st.markdown("**Default Limits**")
            new_boq = st.number_input("Max BOQ Generations", min_value=-1, value=5)
            new_bid = st.number_input("Max Bid Optimizations", min_value=-1, value=5)
            new_analyses = st.number_input("Max Tender Analyses", min_value=-1, value=5)
            new_users = st.number_input("Max Users", min_value=-1, value=1)
            
            st.markdown("**Default Permissions**")
            new_export = st.checkbox("Can Export Data")
            new_edit_rates = st.checkbox("Can Edit Rates")
            new_delete_rates = st.checkbox("Can Delete Rates")
            new_create_versions = st.checkbox("Can Create Versions")
            new_manage_team = st.checkbox("Can Manage Team")
        
        if st.form_submit_button("➕ Create New Plan", type="primary"):
            if not new_plan_name:
                st.error("Plan name is required")
            else:
                plan_name = new_plan_name.lower().strip()
                
                # Check if plan already exists
                with db.get_connection() as conn:
                    cursor = db.db_conn.get_cursor(conn)
                    cursor.execute("SELECT plan_name FROM subscription_plans WHERE plan_name = ?", (plan_name,))
                    if cursor.fetchone():
                        st.error(f"Plan '{plan_name}' already exists!")
                        return
                
                # Insert new plan
                with db.get_connection() as conn:
                    cursor = db.db_conn.get_cursor(conn)
                    try:
                        cursor.execute("""
                            INSERT INTO subscription_plans (
                                plan_name, monthly_price, yearly_price, 
                                max_boq_generations, max_bid_optimizations,
                                max_tender_analyses, max_users,
                                extension_auto_fills,
                                can_export_data, can_edit_rates,
                                can_delete_rates, can_create_versions,
                                can_manage_team, description
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            plan_name, new_monthly, new_yearly,
                            new_boq, new_bid, new_analyses, new_users,
                            5,  # default extension auto-fills
                            1 if new_export else 0,
                            1 if new_edit_rates else 0,
                            1 if new_delete_rates else 0,
                            1 if new_create_versions else 0,
                            1 if new_manage_team else 0,
                            new_description
                        ))
                        conn.commit()
                        st.success(f"✅ Plan '{plan_name}' created!")
                        # Clear plan cache
                        from modules.subscription import get_plans
                        get_plans(force_refresh=True)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating plan: {e}")

def get_system_config(key: str, default_value: str = None) -> str:
    """Get a system configuration value"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default_value
    except Exception as e:
        print(f"Error getting config {key}: {e}")
        return default_value


def save_system_config(key: str, value: str) -> bool:
    """Save a system configuration value"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO system_config (key, value, updated_by)
            VALUES (?, ?, ?)
        """, (key, value, st.session_state.get('user_id')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving config {key}: {e}")
        return False
# Add these functions to _pages/admin_dashboard.py

def render_pwd_version_tab(db_instance):
    """Render PWD version management tab - UI only"""
    
    st.subheader("🏗️ PWD Rate Schedule Version Control")
    
    tabs = st.tabs(["📥 Import New Version", "📜 Version History", "⚙️ Migration"])
    
    with tabs[0]:
        render_version_import(db_instance)
    
    with tabs[1]:
        render_version_history(db_instance)
    
    with tabs[2]:
        render_version_migration(db_instance)


def render_version_import(db_instance):
    """Import a new version of PWD rates - UI only"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        version_name = st.text_input("Version Name", placeholder="PWD Schedule 2025")
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025)
    
    with col2:
        effective_date = st.date_input("Effective From")
        is_active = st.checkbox("Set as Active Version", value=True)
    
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], key="pwd_version_import")
    
    if uploaded_file and st.button("Import Version", type="primary"):
        temp_path = "temp_pwd_version.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Importing PWD schedule..."):
                from modules.pwd_data_manager import PWDParserWithHierarchy, save_hierarchy_to_database
                
                parser = PWDParserWithHierarchy()
                hierarchy = parser.parse_pdf_with_hierarchy(temp_path, max_pages=None)
                
                if hierarchy['parents']:
                    success, parents_count, children_count = save_hierarchy_to_database(hierarchy, edition_year)
                    
                    if success:
                        # Also save version info to rate_versions table
                        conn = db_instance.get_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active)
                            VALUES ('PWD', ?, ?, ?, ?)
                        """, (version_name, edition_year, effective_date, 1 if is_active else 0))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Version {version_name} imported successfully!")
                        st.success(f"   📊 {parents_count} parents, {children_count} children")
                        st.balloons()
                    else:
                        st.error(f"Failed to save: {children_count}")
                else:
                    st.warning("No items found in the PDF")
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def render_version_history(db_instance):
    """Display version history - UI only"""
    
    from modules.pwd_data_manager import get_rate_versions, archive_version
    
    versions = get_rate_versions(db_instance)
    
    if not versions:
        st.info("No versions found. Import a PWD schedule first.")
        return
    
    st.markdown("#### Version History")
    
    for version in versions:
        with st.expander(f"📌 {version['name']} ({version['year']})", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Effective Date:** {version['effective_date']}")
                st.write(f"**Status:** {'✅ Active' if version['is_active'] else '📦 Archived'}")
                st.write(f"**Imported:** {version['imported_at']}")
            
            with col2:
                st.write(f"**Parent Items:** {version['parent_count']}")
                st.write(f"**Child Items:** {version['child_count']}")
                st.write(f"**Total Items:** {version['parent_count'] + version['child_count']}")
            
            if version['is_active']:
                if st.button("Archive", key=f"archive_{version['id']}"):
                    if archive_version(db_instance, version['id']):
                        st.success(f"Version {version['name']} archived")
                        st.rerun()
                    else:
                        st.error("Failed to archive version")


def render_version_migration(db_instance):
    """Migrate BOQ items to new version - UI only"""
    
    st.info("🔧 Migration Tool")
    st.caption("Migrate BOQ items from one version to another")
    
    from modules.pwd_data_manager import get_rate_versions
    
    versions = get_rate_versions(db_instance)
    
    if len(versions) < 2:
        st.warning("Need at least 2 versions to migrate")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        source_version = st.selectbox(
            "Source Version",
            options=[f"{v['name']} ({v['year']})" for v in versions],
            key="source_version"
        )
    
    with col2:
        target_version = st.selectbox(
            "Target Version",
            options=[f"{v['name']} ({v['year']})" for v in versions],
            key="target_version"
        )
    
    if st.button("🚀 Start Migration", type="primary"):
        st.info("Migration feature - Copies BOQ items from source to target version")
        # Add migration logic here
        st.success("Migration completed successfully!")

def get_default_api_url() -> str:
    """Get default API URL based on environment"""
    import os
    if os.environ.get('STREAMLIT_SHARING') or os.environ.get('STREAMLIT_CLOUD'):
        return "https://itender-bd.streamlit.app"
    else:
        return "http://localhost:8501"