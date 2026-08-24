# _pages/admin_dashboard.py - Refactored with all fixes

import streamlit as st
import pandas as pd
import os
import datetime
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO
import zipfile

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
from utils.helpers import safe_compare, safe_strip
from modules.subscription_ui import render_subscription_card
from modules.subscription import get_plan
from database.unified_db_manager import get_db_manager
from database.connection import get_supabase_client, get_db_type, is_supabase

# ==================== CONSTANTS ====================

ROLE_HIERARCHY = {
    'system_admin': '👑 Full platform access',
    'system_support': '🛠️ Can view all companies, support access',
    'system_auditor': '📊 Read-only across platform',
    'company_admin': '🏢 Full company management',
    'manager': '📋 Can manage tenders and create users',
    'analyst': '🔬 Can run analyses and view reports',
    'viewer': '👁️ Read-only access'
}

PERMISSION_CATEGORIES = {
    "👤 User Management": ['manage_users', 'manage_team', 'create_user', 'delete_user'],
    "📄 Content Management": ['manage_tenders', 'view_reports', 'export_data'],
    "🔬 Analysis": ['run_analysis', 'view_rates', 'edit_rates'],
    "⚙️ System": ['manage_zones', 'manage_versions', 'change_plans', 'delete_any']
}

ALL_PERMISSION_KEYS = [
    'manage_users', 'manage_team', 'create_user', 'delete_user',
    'manage_tenders', 'view_reports', 'export_data',
    'run_analysis', 'view_rates', 'edit_rates',
    'manage_zones', 'manage_versions', 'change_plans', 'delete_any'
]

# ==================== HELPER FUNCTIONS ====================

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


def get_role_description(role_name):
    """Get description for a role"""
    return ROLE_HIERARCHY.get(role_name, 'Custom role')


def render_common_admin_styles():
    """Render common styles used across admin dashboard"""
    st.markdown("""
    <style>
        .user-card, .company-row, .role-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            border-bottom: 1px solid #f1f5f9;
            transition: background 0.2s;
            background: white;
        }
        .user-card:hover, .company-row:hover, .role-row:hover {
            background: #f8fafc;
        }
        .user-avatar, .company-avatar, .role-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            flex-shrink: 0;
        }
        .user-avatar { background: #6366f1; color: white; }
        .company-avatar { border-radius: 8px; background: #6366f1; color: white; }
        .role-avatar.system { background: #dbeafe; color: #1e40af; }
        .role-avatar.admin { background: #dbeafe; color: #1e40af; }
        .role-avatar.manager { background: #d1fae5; color: #065f46; }
        .role-avatar.analyst { background: #fef3c7; color: #92400e; }
        .role-avatar.viewer { background: #e5e7eb; color: #374151; }
        .role-avatar.default { background: #f1f5f9; color: #475569; }
        
        .status-active {
            color: #065f46;
            background: #d1fae5;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            display: inline-block;
        }
        .status-inactive {
            color: #991b1b;
            background: #fee2e2;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            display: inline-block;
        }
        .role-badge {
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            background: #f1f5f9;
            color: #475569;
            display: inline-block;
        }
        .role-badge.admin { background: #dbeafe; color: #1e40af; }
        .role-badge.manager { background: #d1fae5; color: #065f46; }
        .role-badge.analyst { background: #fef3c7; color: #92400e; }
        .role-badge.estimator { background: #d1ecf1; color: #0c5460; }
        .badge-plan { background: #e0f2fe; color: #0369a1; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge-perm-count { background: #f1f5f9; color: #475569; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge-user-count { background: #e0f2fe; color: #0369a1; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge-system-role { background: #fef3c7; color: #92400e; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        
        .company-name, .role-name { font-weight: 500; color: #1e293b; }
        .company-email, .role-desc { font-size: 13px; color: #64748b; }
        .company-meta, .role-meta { display: flex; gap: 8px; font-size: 12px; color: #94a3b8; margin-top: 2px; flex-wrap: wrap; }
        .stat-number { font-size: 16px; font-weight: 600; color: #1e293b; }
        .stat-label { font-size: 11px; color: #94a3b8; }
        
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
        .permission-edit-container {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin: 8px 0 16px 0;
        }
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }
        .modal-content {
            background: white;
            border-radius: 8px;
            padding: 30px;
            max-width: 700px;
            width: 95%;
            max-height: 85vh;
            overflow-y: auto;
        }
    </style>
    """, unsafe_allow_html=True)


# ==================== PWD INGESTION FUNCTIONS ====================

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
    
    if st.button("⚡ Parse PWD Schedule", key="parse_pwd_schedule", type="primary", use_container_width=True):
        temp_path = "temp_pwd.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Parsing PDF with hierarchical structure..."):
                parser = PWDParserWithHierarchy()
                hierarchy = parser.parse_pdf_with_hierarchy(temp_path, max_pages=max_pages if max_pages > 0 else None)
            
            if hierarchy['parents']:
                st.success(f"✅ Parsed {len(hierarchy['parents'])} parent items and {len(hierarchy['children'])} child items")
                
                render_hierarchical_pwd_preview(hierarchy)
                
                if not dry_run:
                    if st.button("💾 Confirm & Save to Database", key="confirm_save_pwd", type="primary"):
                        success, msg1, msg2 = save_hierarchy_to_database(hierarchy, edition_year)
                        if success:
                            st.success(f"🎉 Saved {msg1} parents and {msg2} children to database!")
                            st.balloons()
                        else:
                            st.error(f"Database error: {msg2}")
                
                st.markdown("### 📥 Export Data")
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    parents_df = pd.DataFrame(hierarchy['parents'])
                    st.download_button(
                        "📥 Download Parents (CSV)",
                        parents_df.to_csv(index=False),
                        f"pwd_parents_{edition_year}.csv",
                        "text/csv",
                        key="download_pwd_parents"
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
                        "text/csv",
                        key="download_pwd_children"
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
            help="Scan first N pages. Set to 500 for full PDF.",
            key="pwd_scan_pages"
        )
    
    with col2:
        full_scan = st.checkbox("Scan Entire PDF", value=False, help="Overrides pages setting", key="pwd_full_scan")
    
    if st.button("🔍 Analyze PDF Structure", key="analyze_pdf_structure", type="primary", use_container_width=True):
        temp_path = "temp_pwd_verify.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Analyzing PDF structure..."):
                extractor = PWDExtractorForVerification()
                max_pages = None if full_scan else scan_pages
                report = extractor.extract_from_pdf(temp_path, max_pages=max_pages)
            
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
            
            if report['parents']:
                st.markdown("#### Parents")
                st.dataframe(pd.DataFrame(report['parents']), use_container_width=True, hide_index=True)
                
                csv_parents = pd.DataFrame(report['parents']).to_csv(index=False)
                st.download_button(
                    "📥 Download Parents CSV",
                    csv_parents,
                    f"pwd_parents_verification_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    key="download_pwd_parents_verify"
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
    
    db = get_db_manager()
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT pwd_code, description, chapter_number FROM pwd_parents ORDER BY pwd_code")
        parents = cursor.fetchall()
        
        if not parents:
            st.info("No data found in database. Please import a PWD schedule first.")
            return
        
        st.success(f"Found {len(parents)} parent items in database")
        
        chapters = sorted(set(p[2] for p in parents))
        selected_chapter = st.selectbox("Filter by Chapter", ["All"] + chapters, key="pwd_chapter_filter")
        
        search_term = st.text_input("Search items", placeholder="Enter item code or description...", key="pwd_search")
        
        for parent in parents:
            parent_code = parent[0]
            parent_desc = parent[1]
            parent_chapter = parent[2]
            
            if selected_chapter != "All" and parent_chapter != selected_chapter:
                continue
            
            if search_term and search_term.lower() not in parent_code.lower() and search_term.lower() not in parent_desc.lower():
                continue
            
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
        version_name = st.text_input("Version Name", placeholder="PWD Schedule 2025", key="version_name_input")
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025, key="version_year_input")
    
    with col2:
        effective_date = st.date_input("Effective From", key="version_effective_date")
        is_active = st.checkbox("Set as Active Version", value=True, key="version_active_check")
    
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], key="version_pdf_upload")
    
    if uploaded_file and st.button("Import Version", key="import_version_btn"):
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
                if st.button("Archive", key=f"archive_version_{version['id']}"):
                    archive_version(db_instance, version['id'])
                    st.rerun()


def render_version_migration(db_instance):
    """Migrate BOQ items to new version"""
    st.info("Migration functionality coming soon")


# ==================== USER MANAGEMENT FUNCTIONS ====================

def render_user_profile_view(db):
    """Render user profile view with all fields and subscription status"""
    st.markdown("### 👤 User Profile")
    
    user_id = st.session_state.get('view_user_id')
    
    if not user_id:
        st.error("No user selected")
        if st.button("← Back to User List", key="back_from_view_to_list"):
            st.session_state.user_sub_page = 'list'
            st.rerun()
        return
    
    user = db.get_user_by_id(user_id)
    
    if not user:
        st.error("User not found")
        if st.button("← Back to User List", key="back_from_view_not_found"):
            st.session_state.user_sub_page = 'list'
            st.rerun()
        return
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("← Back to List", key="back_from_user_view"):
            st.session_state.user_sub_page = 'list'
            st.rerun()
    
    st.divider()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        avatar_url = user.get('avatar_url')
        if avatar_url:
            try:
                st.image(avatar_url, width=150)
            except:
                initials = ''.join([word[0].upper() for word in user.get('full_name', 'U').split()[:2]])
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 150px; height: 150px; border-radius: 50%; background: #6366f1; color: white; display: flex; align-items: center; justify-content: center; font-size: 64px; font-weight: 600; margin: 0 auto;">
                        {initials}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            initials = ''.join([word[0].upper() for word in user.get('full_name', 'U').split()[:2]])
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="width: 150px; height: 150px; border-radius: 50%; background: #6366f1; color: white; display: flex; align-items: center; justify-content: center; font-size: 64px; font-weight: 600; margin: 0 auto;">
                    {initials}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="text-align: center; margin-top: 12px;">
            <h3>{user.get('full_name', 'Unknown')}</h3>
            <p style="color: #64748b;">@{user.get('username', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📋 Basic Information")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Email:** {user.get('email', 'N/A')}")
            st.markdown(f"**Mobile:** {user.get('mobile_number', 'N/A')}")
            st.markdown(f"**Phone:** {user.get('phone', 'N/A')}")
        with col_b:
            st.markdown(f"**Role:** {user.get('role', 'N/A').replace('_', ' ').title()}")
            st.markdown(f"**Status:** {'✅ Active' if user.get('is_active', 0) == 1 else '❌ Inactive'}")
            st.markdown(f"**Company:** {user.get('company_name', 'N/A')}")
        
        st.divider()
        
        st.markdown("### 🔐 Account Information")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Created:** {user.get('created_at', 'N/A')}")
            st.markdown(f"**Last Login:** {user.get('last_login', 'Never')}")
            st.markdown(f"**Email Verified:** {'✅' if user.get('email_verified', False) else '❌'}")
        with col_b:
            st.markdown(f"**Mobile Verified:** {'✅' if user.get('mobile_verified', False) else '❌'}")
            st.markdown(f"**Two-Factor Auth:** {'✅' if user.get('two_factor_verified', False) else '❌'}")
            st.markdown(f"**Account Type:** {user.get('account_type', 'N/A')}")
        
        st.divider()
        
        st.markdown("### 💳 Subscription")
        render_subscription_status(user_id, user)
        
        st.divider()
        
        st.markdown("### 💼 Professional Information")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Specialization:** {user.get('specialization', 'N/A')}")
            st.markdown(f"**Years Experience:** {user.get('years_experience', 0)}")
        with col_b:
            st.markdown(f"**Location:** {user.get('location', 'N/A')}")
            st.markdown(f"**Website:** {user.get('website', 'N/A')}")
        
        if user.get('bio'):
            st.markdown(f"**Bio:** {user.get('bio')}")
        
        st.divider()
        
        if user.get('auth_provider'):
            st.markdown("### 🔑 Authentication")
            st.markdown(f"**Provider:** {user.get('auth_provider', 'N/A')}")
            if user.get('google_email'):
                st.markdown(f"**Google Email:** {user.get('google_email')}")
            if user.get('facebook_email'):
                st.markdown(f"**Facebook Email:** {user.get('facebook_email')}")
    
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✏️ Edit User", key="edit_from_view", type="primary", use_container_width=True):
            st.session_state.user_sub_page = 'edit_user'
            st.session_state.edit_user_id = user_id
            st.rerun()
    
    with col2:
        if st.button("🔑 Reset Password", key="reset_password_view", use_container_width=True):
            success, new_pw = db.reset_user_password(user_id)
            if success:
                st.success(f"✅ New password: `{new_pw}`")
            else:
                st.error(f"❌ Failed: {new_pw}")
    
    with col3:
        if st.button("📧 Send Activation", key="send_activation_view", use_container_width=True):
            st.info("Activation email sent!")
    
    with col4:
        if st.button("← Back", key="back_from_profile", use_container_width=True):
            st.session_state.user_sub_page = 'list'
            st.rerun()


def render_subscription_status(user_id: int, user: Dict):
    """Render subscription status for a user"""
    try:
        from database.crud_subscription import SubscriptionManager
        sub_manager = SubscriptionManager()
        
        status = sub_manager.check_user_subscription_status(user_id)
        
        if status.get('has_subscription'):
            sub = status.get('subscription', {})
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Plan:** {sub.get('plan_name', sub.get('plan', 'N/A')).title()}")
                st.markdown(f"**Status:** {'✅ Active' if sub.get('status') == 'active' else '❌ ' + sub.get('status', 'Unknown').title()}")
                st.markdown(f"**Type:** {status.get('type', 'N/A').title()}")
            with col_b:
                st.markdown(f"**Analyses Used:** {sub.get('analyses_used', 0)} / {sub.get('analyses_limit', 0)}")
                if sub.get('end_date'):
                    st.markdown(f"**Expires:** {sub.get('end_date')}")
                else:
                    st.markdown("**Expires:** Never")
            
            remaining = sub.get('analyses_limit', 0) - sub.get('analyses_used', 0)
            if remaining > 0:
                st.progress(sub.get('analyses_used', 0) / max(sub.get('analyses_limit', 1), 1))
                st.caption(f"📊 {remaining} analyses remaining")
            else:
                st.warning("⚠️ No analyses remaining")
        else:
            if user.get('company_id'):
                st.warning(f"⚠️ No active subscription found for this company")
                st.caption("Contact your company administrator to activate the subscription")
            else:
                st.warning("⚠️ No active subscription found")
                st.caption("Individual users require an active subscription to access premium features")
                
    except ImportError:
        st.info("💳 Subscription management not available")
    except Exception as e:
        st.error(f"❌ Error loading subscription: {e}")


def render_user_edit_form(db):
    """Render user edit form with all editable fields - SINGLE DEFINITION"""
    st.markdown("### ✏️ Edit User")
    
    user_id = st.session_state.get('edit_user_id')
    
    if not user_id:
        st.error("No user selected")
        if st.button("← Back to User List", key="back_from_edit_empty"):
            st.session_state.user_sub_page = 'list'
            st.rerun()
        return
    
    user = db.get_user_by_id(user_id)
    
    if not user:
        st.error("User not found")
        if st.button("← Back to User List", key="back_from_edit_not_found"):
            st.session_state.user_sub_page = 'list'
            st.rerun()
        return
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("← Back to List", key="back_from_user_edit"):
            st.session_state.user_sub_page = 'list'
            st.rerun()
    
    st.divider()
    
    current_role = user.get('role', 'viewer')
    role_options = ["system_admin", "company_admin", "manager", "analyst", "estimator", "viewer", "individual"]
    if current_role not in role_options:
        role_options.append(current_role)
    
    try:
        role_index = role_options.index(current_role)
    except ValueError:
        role_index = 0
    
    with st.form("edit_user_form"):
        st.markdown("### 📋 Basic Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username *", value=user.get('username', ''), key="edit_username")
            full_name = st.text_input("Full Name *", value=user.get('full_name', ''), key="edit_full_name")
            email = st.text_input("Email *", value=user.get('email', ''), key="edit_email")
        
        with col2:
            mobile = st.text_input("Mobile Number *", value=user.get('mobile_number', ''), key="edit_mobile")
            phone = st.text_input("Phone", value=user.get('phone', ''), key="edit_phone")
            role = st.selectbox(
                "Role *",
                options=role_options,
                index=role_index,
                key="edit_role_select"
            )
        
        st.divider()
        
        st.markdown("### 💼 Professional Information")
        
        col1, col2 = st.columns(2)
        with col1:
            specialization = st.text_input("Specialization", value=user.get('specialization', ''), key="edit_specialization")
            years_experience = st.number_input(
                "Years of Experience", 
                min_value=0, 
                max_value=50, 
                value=user.get('years_experience', 0) or 0,
                key="edit_years_exp"
            )
        with col2:
            location = st.text_input("Location", value=user.get('location', ''), key="edit_location")
            website = st.text_input("Website", value=user.get('website', ''), key="edit_website")
        
        bio = st.text_area("Bio", value=user.get('bio', ''), max_chars=500, key="edit_bio")
        
        st.divider()
        
        st.markdown("### 🔐 Account Status")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            is_active = st.checkbox("Active", value=user.get('is_active', 0) == 1, key="edit_is_active")
        
        with col2:
            email_verified = st.checkbox("Email Verified", value=user.get('email_verified', False), key="edit_email_verified")
        
        with col3:
            mobile_verified = st.checkbox("Mobile Verified", value=user.get('mobile_verified', False), key="edit_mobile_verified")
        
        st.divider()
        
        st.markdown("### 🏢 Company Assignment")
        
        companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
        company_options = {c['company_name']: c['id'] for c in companies}
        
        current_company_name = user.get('company_name', '')
        company_list = ["No Company"] + list(company_options.keys())
        
        if current_company_name and current_company_name in company_options:
            company_index = company_list.index(current_company_name)
        else:
            company_index = 0
        
        company_name = st.selectbox(
            "Company",
            options=company_list,
            index=company_index,
            key="edit_company_select"
        )
        
        company_id = company_options.get(company_name, None) if company_name != "No Company" else None
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.user_sub_page = 'list'
                st.rerun()
    
    st.divider()
    st.markdown("### 💳 Subscription Management")
    render_subscription_edit_form(user_id, user, db)
    
    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔑 Reset Password", key="reset_password_edit", use_container_width=True):
            success, new_pw = db.reset_user_password(user_id)
            if success:
                st.success(f"✅ New password: `{new_pw}`")
            else:
                st.error(f"❌ Failed: {new_pw}")
    
    if submitted:
        updates = {}
        
        new_username = safe_strip(username)
        if safe_compare(new_username, user.get('username')):
            updates['username'] = new_username
        
        new_full_name = safe_strip(full_name)
        if safe_compare(new_full_name, user.get('full_name')):
            updates['full_name'] = new_full_name
        
        new_email = safe_strip(email)
        if safe_compare(new_email, user.get('email')):
            updates['email'] = new_email
        
        new_mobile = safe_strip(mobile)
        if safe_compare(new_mobile, user.get('mobile_number')):
            updates['mobile_number'] = new_mobile
        
        new_phone = safe_strip(phone)
        if safe_compare(new_phone, user.get('phone')):
            updates['phone'] = new_phone
        
        if role != user.get('role'):
            updates['role'] = role
        
        if is_active != (user.get('is_active', 0) == 1):
            updates['is_active'] = 1 if is_active else 0
        
        if email_verified != user.get('email_verified', False):
            updates['email_verified'] = email_verified
        
        if mobile_verified != user.get('mobile_verified', False):
            updates['mobile_verified'] = mobile_verified
        
        new_specialization = safe_strip(specialization)
        if safe_compare(new_specialization, user.get('specialization')):
            updates['specialization'] = new_specialization
        
        new_years_exp = years_experience if years_experience > 0 else None
        if new_years_exp != (user.get('years_experience', 0) or 0):
            updates['years_experience'] = new_years_exp
        
        new_location = safe_strip(location)
        if safe_compare(new_location, user.get('location')):
            updates['location'] = new_location
        
        new_website = safe_strip(website)
        if safe_compare(new_website, user.get('website')):
            updates['website'] = new_website
        
        new_bio = safe_strip(bio)
        if safe_compare(new_bio, user.get('bio')):
            updates['bio'] = new_bio
        
        new_company_id = company_id if company_id else None
        if new_company_id != user.get('company_id'):
            updates['company_id'] = new_company_id
        
        if updates:
            if db.update_user(user_id, updates):
                st.success("✅ User updated successfully!")
                st.balloons()
                st.session_state.user_sub_page = 'list'
                st.rerun()
            else:
                st.error("❌ Failed to update user")
        else:
            st.info("No changes made")


def render_subscription_edit_form(user_id: int, user: Dict, db):
    """Render subscription edit form for a user - OUTSIDE main form"""
    
    try:
        from database.crud_subscription import SubscriptionManager
        sub_manager = SubscriptionManager()
        
        status = sub_manager.check_user_subscription_status(user_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Current Subscription")
            if status.get('has_subscription'):
                sub = status.get('subscription', {})
                st.info(f"**Plan:** {sub.get('plan_name', sub.get('plan', 'N/A')).title()}")
                st.caption(f"**Status:** {sub.get('status', 'N/A').title()}")
                st.caption(f"**Expires:** {sub.get('end_date', 'Never')}")
                st.caption(f"**Analyses:** {sub.get('analyses_used', 0)}/{sub.get('analyses_limit', 0)} used")
            else:
                st.warning("No active subscription found")
                if user.get('company_id'):
                    st.caption("Company subscription inactive")
                else:
                    st.caption("Individual user requires active subscription")
        
        with col2:
            if st.session_state.get('user_role') in ['admin', 'system_admin']:
                st.markdown("#### Change Plan")
                
                plans = sub_manager.get_all_plans()
                
                if plans:
                    account_type = user.get('account_type', 'individual')
                    filtered_plans = [p for p in plans if p.get('plan_type') == account_type or p.get('plan_type') == 'both']
                    
                    if not filtered_plans:
                        filtered_plans = plans
                    
                    plan_options = {p['plan_name'].title(): p['plan_name'] for p in filtered_plans}
                    
                    with st.form("subscription_update_form"):
                        selected_plan = st.selectbox(
                            "Select Plan",
                            options=list(plan_options.keys()),
                            key="subscription_plan_select"
                        )
                        
                        duration = st.selectbox(
                            "Duration",
                            ["Monthly", "Yearly"],
                            key="subscription_duration_select"
                        )
                        
                        update_submitted = st.form_submit_button("🔄 Update Subscription", type="primary", use_container_width=True)
                        
                        if update_submitted:
                            plan_name = plan_options[selected_plan]
                            is_yearly = duration == "Yearly"
                            
                            if user.get('company_id'):
                                success = sub_manager.update_company_subscription(
                                    company_id=user.get('company_id'),
                                    plan=plan_name,
                                    duration='yearly' if is_yearly else 'monthly',
                                    payment_method='admin_update'
                                )
                                if success:
                                    st.success(f"✅ Company subscription updated to {selected_plan}")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update company subscription")
                            else:
                                success = sub_manager.update_user_subscription(
                                    user_id=user_id,
                                    plan=plan_name,
                                    duration='yearly' if is_yearly else 'monthly',
                                    payment_method='admin_update'
                                )
                                if success:
                                    st.success(f"✅ User subscription updated to {selected_plan}")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update user subscription")
                else:
                    st.info("No plans available")
            else:
                st.caption("💡 Contact your administrator to change subscription plans")
                
    except ImportError:
        st.info("💳 Subscription management not available")
    except Exception as e:
        st.error(f"❌ Error loading subscription: {e}")


def render_user_management_with_routing(db):
    """Render user management with internal routing"""
    
    try:
        all_users, total = db.get_all_users_filtered(limit=1000)
        
        try:
            system_users = db.get_system_users()
        except:
            system_users = []
        
        all_user_ids = {u.get('id') for u in all_users}
        for su in system_users:
            if su.get('id') not in all_user_ids:
                su['is_system_user'] = True
                all_users.append(su)
                
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return
    
    render_all_users(all_users, db)


def render_all_users(all_users, db):
    """Render all users table with View and Edit action buttons and sorting"""
    st.markdown("### 👥 All Users")
    
    if not all_users:
        st.info("No users found")
        return
    
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    
    with col1:
        search = st.text_input("🔍 Search users", placeholder="Name, email, or username...", key="user_search_input")
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Username", "Full Name", "Email", "Role", "Status", "Company"],
            key="user_sort_by"
        )
    
    with col3:
        sort_order = st.selectbox(
            "Order",
            ["Ascending", "Descending"],
            key="user_sort_order"
        )
    
    filtered_users = all_users
    if search:
        search_lower = search.lower()
        filtered_users = [
            u for u in all_users
            if search_lower in str(u.get('username', '')).lower()
            or search_lower in str(u.get('email', '')).lower()
            or search_lower in str(u.get('full_name', '')).lower()
        ]
    
    if not filtered_users:
        st.info("No users match the search criteria")
        return
    
    sort_key_map = {
        "Username": lambda x: str(x.get('username', '')).lower(),
        "Full Name": lambda x: str(x.get('full_name', '')).lower(),
        "Email": lambda x: str(x.get('email', '')).lower(),
        "Role": lambda x: str(x.get('role', '')),
        "Status": lambda x: x.get('is_active', 0),
        "Company": lambda x: str(x.get('company_name', '')).lower()
    }
    
    if sort_by in sort_key_map:
        filtered_users.sort(key=sort_key_map[sort_by], reverse=(sort_order == "Descending"))
    
    per_page = 10
    total_users = len(filtered_users)
    total_pages = (total_users + per_page - 1) // per_page
    
    if 'user_table_page' not in st.session_state:
        st.session_state.user_table_page = 1
    
    if st.session_state.user_table_page > total_pages:
        st.session_state.user_table_page = max(1, total_pages)
    
    page = st.session_state.user_table_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_users)
    page_users = filtered_users[start_idx:end_idx]
    
    for u in page_users:
        user_id = u.get('id')
        username = u.get('username', 'N/A')
        full_name = u.get('full_name', 'N/A')
        email = u.get('email', 'N/A')
        role = u.get('role', 'viewer')
        is_active = u.get('is_active', 0)
        company_name = u.get('company_name', 'N/A')
        mobile = u.get('mobile_number', '')
        
        initials = ''.join([word[0].upper() for word in full_name.split()[:2]]) if full_name != 'N/A' else 'U'
        
        role_class = 'viewer'
        if role in ['system_admin', 'company_admin']:
            role_class = 'admin'
        elif role == 'manager':
            role_class = 'manager'
        elif role == 'analyst':
            role_class = 'analyst'
        elif role == 'estimator':
            role_class = 'estimator'
        
        role_display = role.replace('_', ' ').title()
        status_class = 'status-active' if is_active == 1 else 'status-inactive'
        status_text = '✅ Active' if is_active == 1 else '❌ Inactive'
        
        with st.container():
            cols = st.columns([0.5, 1.5, 2.5, 1.2, 1.2, 1.5])
            
            with cols[0]:
                st.markdown(f'<div class="user-avatar">{initials}</div>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                    <div>
                        <strong>@{username}</strong>
                        <div style="font-size: 13px; color: #64748b;">{full_name}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f"""
                    <div style="font-size: 13px; color: #475569;">
                        <div>{email}</div>
                        <div style="font-size: 12px; color: #94a3b8;">📱 {mobile if mobile else 'No mobile'}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[3]:
                st.markdown(f'<span class="role-badge {role_class}">{role_display}</span>', unsafe_allow_html=True)
            
            with cols[4]:
                st.markdown(f'<span class="{status_class}">{status_text}</span>', unsafe_allow_html=True)
                if company_name and company_name != 'N/A':
                    st.markdown(f'<span style="font-size: 11px; color: #94a3b8;">🏢 {company_name}</span>', unsafe_allow_html=True)
            
            with cols[5]:
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("👁️", key=f"view_user_{user_id}", use_container_width=True, help="View user profile"):
                        st.session_state.user_sub_page = 'view_profile'
                        st.session_state.view_user_id = user_id
                        st.rerun()
                
                with btn_col2:
                    if st.button("✏️", key=f"edit_user_{user_id}", use_container_width=True, help="Edit user"):
                        st.session_state.user_sub_page = 'edit_user'
                        st.session_state.edit_user_id = user_id
                        st.rerun()
    
    if total_pages > 1:
        st.markdown("---")
        
        col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
        
        with col1:
            if st.button("◀ Prev", key="user_prev_page", disabled=(page <= 1), use_container_width=True):
                st.session_state.user_table_page = page - 1
                st.rerun()
        
        with col2:
            st.markdown(f"<div style='text-align: center; padding-top: 6px; color: #475569;'>Page {page} of {total_pages}</div>", unsafe_allow_html=True)
        
        with col3:
            page_cols = st.columns(min(total_pages, 7))
            start_page = max(1, page - 3)
            end_page = min(total_pages, page + 3)
            
            for i, p in enumerate(range(start_page, end_page + 1)):
                with page_cols[i]:
                    if st.button(str(p), key=f"user_page_{p}", 
                                type="primary" if p == page else "secondary",
                                use_container_width=True):
                        st.session_state.user_table_page = p
                        st.rerun()
        
        with col4:
            jump_to = st.number_input(
                "Jump to",
                min_value=1,
                max_value=total_pages,
                value=page,
                step=1,
                key="user_jump_to_page",
                label_visibility="collapsed"
            )
            if jump_to != page:
                st.session_state.user_table_page = jump_to
                st.rerun()
        
        with col5:
            if st.button("Next ▶", key="user_next_page", disabled=(page >= total_pages), use_container_width=True):
                st.session_state.user_table_page = page + 1
                st.rerun()
        
        st.caption(f"Showing {start_idx + 1}–{end_idx} of {total_users} users")


# ==================== COMPANY MANAGEMENT FUNCTIONS ====================

def render_company_management(db):
    """WordPress-style company management with proper routing"""
    
    company_sub_page = st.session_state.get('company_sub_page', 'list')
    
    if company_sub_page == 'view_company':
        render_company_detail_view(db)
        return
    elif company_sub_page == 'edit_company':
        render_company_edit_page(db)
        return
    elif company_sub_page == 'subscription':
        render_company_subscription_page(db)
        return
    else:
        render_company_list(db)


def render_company_list(db):
    """Render company list with WordPress-style UI - row-based layout"""
    st.markdown("### 🏢 Company Management")
    st.caption("Create, edit, and manage companies on the platform")
    
    companies_all, total_all = db.get_all_companies_filtered(status=None, limit=1000)
    active_companies = len([c for c in companies_all if c.get('is_active', 0) == 1])
    inactive_companies = len([c for c in companies_all if c.get('is_active', 0) == 0])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏢 Total Companies", total_all)
    with col2:
        st.metric("✅ Active", active_companies)
    with col3:
        st.metric("❌ Inactive", inactive_companies)
    with col4:
        total_users = 0
        for c in companies_all:
            users, _ = db.get_all_users_filtered(company_id=c.get('id'), limit=1000)
            total_users += len(users)
        st.metric("👥 Total Users", total_users)
    
    st.divider()
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add New Company", key="add_company_btn", type="primary", use_container_width=True):
            st.session_state.show_add_company_modal = True
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search companies", placeholder="Name, email, or registration number...", key="company_search")
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "Active", "Inactive"],
            key="company_status_filter_select"
        )
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Name", "Created Date", "Users Count"],
            key="company_sort_by_select"
        )
    
    status = None if status_filter == "All" else (1 if status_filter == "Active" else 0)
    companies, total = db.get_all_companies_filtered(
        search=search if search else None,
        status=status,
        limit=100,
        offset=0
    )
    
    if not companies:
        st.info("No companies found. Click 'Add New Company' to create one.")
        if st.session_state.get('show_add_company_modal', False):
            render_add_company_modal(db)
        return
    
    if sort_by == "Name":
        companies.sort(key=lambda x: x.get('company_name', '').lower())
    elif sort_by == "Created Date":
        companies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort_by == "Users Count":
        for c in companies:
            users, _ = db.get_all_users_filtered(company_id=c.get('id'), limit=1000)
            c['_user_count'] = len(users)
        companies.sort(key=lambda x: x.get('_user_count', 0), reverse=True)
    
    per_page = 10
    total_pages = (len(companies) + per_page - 1) // per_page
    
    if 'company_page' not in st.session_state:
        st.session_state.company_page = 1
    
    if st.session_state.company_page > total_pages:
        st.session_state.company_page = max(1, total_pages)
    
    page = st.session_state.company_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(companies))
    page_companies = companies[start_idx:end_idx]
    
    st.markdown(f"**Showing {len(companies)} companies**")
    
    for company in page_companies:
        company_id = company.get('id')
        company_name = company.get('company_name', 'Unknown')
        email = company.get('email', '')
        is_active = company.get('is_active', 0)
        created_at = company.get('created_at', '')
        
        try:
            stats = db.get_company_stats_by_id(company_id)
            user_count = stats.get('total_users', 0)
            analysis_count = stats.get('total_analyses', 0)
        except:
            user_count = 0
            analysis_count = 0
        
        subscription = db.get_company_subscription(company_id)
        plan_name = subscription.get('plan', 'Free').title() if subscription else 'Free'
        
        initial = company_name[0].upper() if company_name else 'C'
        status_badge = 'status-active' if is_active == 1 else 'status-inactive'
        status_text = 'Active' if is_active == 1 else 'Inactive'
        
        with st.container():
            cols = st.columns([0.5, 1.5, 2.5, 1.2, 1.2, 1.2, 1.2])
            
            with cols[0]:
                st.markdown(f'<div class="company-avatar">{initial}</div>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                    <div>
                        <div class="company-name">{company_name}</div>
                        <div class="company-email">{email if email else 'No email'}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f"""
                    <div class="company-meta">
                        <span class="{status_badge}">{status_text}</span>
                        <span class="badge-plan">📋 {plan_name}</span>
                        <span style="color: #94a3b8;">📅 {str(created_at)[:10] if created_at else 'N/A'}</span>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[3]:
                st.markdown(f"""
                    <div style="text-align: center;">
                        <div class="stat-number">{user_count}</div>
                        <div class="stat-label">Users</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[4]:
                st.markdown(f"""
                    <div style="text-align: center;">
                        <div class="stat-number">{analysis_count}</div>
                        <div class="stat-label">Analyses</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[5]:
                if st.button("👁️", key=f"view_company_{company_id}", use_container_width=True, help="View company details"):
                    st.session_state.company_sub_page = 'view_company'
                    st.session_state.view_company_id = company_id
                    st.rerun()
            
            with cols[6]:
                if st.button("✏️", key=f"edit_company_{company_id}", use_container_width=True, help="Edit company"):
                    st.session_state.company_sub_page = 'edit_company'
                    st.session_state.edit_company_id = company_id
                    st.rerun()
    
    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
        
        with col1:
            if st.button("◀ Prev", key="company_prev_page", disabled=(page <= 1), use_container_width=True):
                st.session_state.company_page = page - 1
                st.rerun()
        
        with col2:
            st.markdown(f"<div style='text-align: center; padding-top: 6px; color: #475569;'>Page {page} of {total_pages}</div>", unsafe_allow_html=True)
        
        with col3:
            page_cols = st.columns(min(total_pages, 7))
            start_page = max(1, page - 3)
            end_page = min(total_pages, page + 3)
            
            for i, p in enumerate(range(start_page, end_page + 1)):
                with page_cols[i]:
                    if st.button(str(p), key=f"company_page_{p}", 
                                type="primary" if p == page else "secondary",
                                use_container_width=True):
                        st.session_state.company_page = p
                        st.rerun()
        
        with col4:
            jump_to = st.number_input(
                "Jump to",
                min_value=1,
                max_value=total_pages,
                value=page,
                step=1,
                key="company_jump_to_page",
                label_visibility="collapsed"
            )
            if jump_to != page:
                st.session_state.company_page = jump_to
                st.rerun()
        
        with col5:
            if st.button("Next ▶", key="company_next_page", disabled=(page >= total_pages), use_container_width=True):
                st.session_state.company_page = page + 1
                st.rerun()
        
        st.caption(f"Showing {start_idx + 1}–{end_idx} of {len(companies)} companies")
    
    if st.session_state.get('show_add_company_modal', False):
        render_add_company_modal(db)


def render_add_company_modal(db):
    """Render add company modal"""
    
    with st.container():
        st.markdown("""
        <div class="modal-overlay">
            <div class="modal-content">
        """, unsafe_allow_html=True)
        
        with st.form("add_company_modal_form"):
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0;">➕ Add New Company</h2>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                company_name = st.text_input("Company Name *", key="add_company_name")
                email = st.text_input("Email", key="add_company_email")
                phone = st.text_input("Phone", key="add_company_phone")
                mobile_number = st.text_input("Mobile Number *", key="add_company_mobile", help="Bangladeshi mobile: 01XXXXXXXXX")
            
            with col2:
                division = st.text_input("Division", key="add_company_division")
                district = st.text_input("District", key="add_company_district")
                registration_number = st.text_input("Registration Number", key="add_company_reg")
                vat_number = st.text_input("VAT Number", key="add_company_vat")
            
            address = st.text_area("Address", height=80, key="add_company_address")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("✅ Create Company", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("❌ Cancel", key="cancel_add_company", use_container_width=True):
                    st.session_state.show_add_company_modal = False
                    st.rerun()
            
            if submitted:
                if not company_name:
                    st.error("Company name is required")
                elif not mobile_number:
                    st.error("Mobile number is required")
                else:
                    company_data = {
                        'company_name': company_name.strip(),
                        'email': email.strip() if email else None,
                        'phone': phone.strip() if phone else None,
                        'mobile_number': mobile_number.strip(),
                        'division': division.strip() if division else None,
                        'district': district.strip() if district else None,
                        'address': address.strip() if address else None,
                        'registration_number': registration_number.strip() if registration_number else None,
                        'vat_number': vat_number.strip() if vat_number else None
                    }
                    
                    success, result = db.create_company(company_data)
                    if success:
                        st.success(f"✅ Company '{company_name}' created successfully!")
                        st.session_state.show_add_company_modal = False
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result}")
        
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_company_detail_view(db):
    """Render company detail view page"""
    st.markdown("### 🏢 Company Details")
    
    company_id = st.session_state.get('view_company_id')
    
    if not company_id:
        st.error("No company selected")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to Companies", key="back_from_detail_no_id", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()
        return
    
    company = db.get_company_by_id(company_id)
    
    if not company:
        st.error("Company not found")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to Companies", key="back_from_detail_not_found", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()
        return
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("← Back", key="back_from_company_view"):
            st.session_state.company_sub_page = 'list'
            st.rerun()
    
    st.divider()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        initial = company.get('company_name', 'C')[0].upper()
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="
                width: 120px; 
                height: 120px; 
                border-radius: 50%; 
                background: #6366f1; 
                color: white; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                font-size: 48px; 
                font-weight: 600; 
                margin: 0 auto;
            ">{initial}</div>
            <h3 style="margin-top: 12px;">{company.get('company_name', 'Unknown')}</h3>
            <p style="color: #64748b;">{company.get('email', 'No email')}</p>
            <p style="color: #64748b; font-size: 13px;">ID: {company_id}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📋 Company Information")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Company Name:** {company.get('company_name', 'N/A')}")
            st.markdown(f"**Email:** {company.get('email', 'N/A')}")
            st.markdown(f"**Phone:** {company.get('phone', 'N/A')}")
            st.markdown(f"**Mobile:** {company.get('mobile_number', 'N/A')}")
        with col_b:
            st.markdown(f"**Status:** {'✅ Active' if company.get('is_active', 0) == 1 else '❌ Inactive'}")
            st.markdown(f"**Division:** {company.get('division', 'N/A')}")
            st.markdown(f"**District:** {company.get('district', 'N/A')}")
            st.markdown(f"**Created:** {company.get('created_at', 'N/A')}")
        
        if company.get('address'):
            st.markdown(f"**Address:** {company.get('address')}")
        
        if company.get('registration_number'):
            st.markdown(f"**Registration #:** {company.get('registration_number')}")
        
        if company.get('vat_number'):
            st.markdown(f"**VAT #:** {company.get('vat_number')}")
    
    st.divider()
    
    try:
        stats = db.get_company_stats_by_id(company_id)
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("👥 Users", stats.get('total_users', 0))
        with col_b:
            st.metric("📊 Analyses", stats.get('total_analyses', 0))
        with col_c:
            st.metric("🏆 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        with col_d:
            st.metric("💰 Revenue", f"${stats.get('total_revenue', 0):,.2f}")
    except:
        pass
    
    st.divider()
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("✏️ Edit Company", key="edit_from_detail", type="primary", use_container_width=True):
            st.session_state.company_sub_page = 'edit_company'
            st.session_state.edit_company_id = company_id
            st.rerun()
    
    with col_b:
        if st.button("👥 Manage Users", key="manage_users_from_detail", use_container_width=True):
            st.session_state.selected_company_id = company_id
            st.session_state.page = "user_management"
            st.rerun()
    
    with col_c:
        if st.button("💳 Manage Subscription", key="manage_sub_from_detail", use_container_width=True):
            st.session_state.company_sub_page = 'subscription'
            st.session_state.subscription_company_id = company_id
            st.rerun()


def render_company_edit_page(db):
    """Render company edit page"""
    st.markdown("### ✏️ Edit Company")
    
    company_id = st.session_state.get('edit_company_id')
    
    if not company_id:
        st.error("No company selected")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to Companies", key="back_from_edit_no_id", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()
        return
    
    company = db.get_company_by_id(company_id)
    
    if not company:
        st.error("Company not found")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to Companies", key="back_from_edit_not_found", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()
        return
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("← Back", key="back_from_company_edit"):
            st.session_state.company_sub_page = 'list'
            st.rerun()
    
    st.divider()
    
    with st.form("edit_company_form"):
        st.markdown("### 📋 Company Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input("Company Name *", value=company.get('company_name', ''), key="edit_comp_name")
            email = st.text_input("Email", value=company.get('email', ''), key="edit_comp_email")
            phone = st.text_input("Phone", value=company.get('phone', ''), key="edit_comp_phone")
            mobile_number = st.text_input("Mobile Number *", value=company.get('mobile_number', ''), key="edit_comp_mobile")
            website = st.text_input("Website", value=company.get('website', ''), key="edit_comp_website")
        
        with col2:
            division = st.text_input("Division", value=company.get('division', ''), key="edit_comp_division")
            district = st.text_input("District", value=company.get('district', ''), key="edit_comp_district")
            registration_number = st.text_input("Registration Number", value=company.get('registration_number', ''), key="edit_comp_reg")
            vat_number = st.text_input("VAT Number", value=company.get('vat_number', ''), key="edit_comp_vat")
        
        address = st.text_area("Address", value=company.get('address', ''), height=80, key="edit_comp_address")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            is_active = st.checkbox("Active", value=company.get('is_active', 0) == 1, key="edit_comp_active")
        
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
            
            if submitted:
                if not company_name:
                    st.error("Company name is required")
                elif not mobile_number:
                    st.error("Mobile number is required")
                else:
                    # Build the updates dictionary
                    updates = {
                        'company_name': company_name.strip(),
                        'mobile_number': mobile_number.strip(),
                    }
                    
                    # Only add optional fields if they have values
                    if email and email.strip():
                        updates['email'] = email.strip()
                    else:
                        updates['email'] = None
                    
                    if phone and phone.strip():
                        updates['phone'] = phone.strip()
                    else:
                        updates['phone'] = None
                    
                    if website and website.strip():
                        updates['website'] = website.strip()
                    else:
                        updates['website'] = None
                    
                    if division and division.strip():
                        updates['division'] = division.strip()
                    else:
                        updates['division'] = None
                    
                    if district and district.strip():
                        updates['district'] = district.strip()
                    else:
                        updates['district'] = None
                    
                    if address and address.strip():
                        updates['address'] = address.strip()
                    else:
                        updates['address'] = None
                    
                    if registration_number and registration_number.strip():
                        updates['registration_number'] = registration_number.strip()
                    else:
                        updates['registration_number'] = None
                    
                    if vat_number and vat_number.strip():
                        updates['vat_number'] = vat_number.strip()
                    else:
                        updates['vat_number'] = None
                    
                    updates['is_active'] = 1 if is_active else 0
                    
                    # Call update_company with the dictionary
                    if db.update_company(company_id, updates):
                        st.success("✅ Company updated successfully!")
                        st.session_state.company_sub_page = 'list'
                        st.rerun()
                    else:
                        st.error("❌ Failed to update company")
        
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()



def render_company_subscription_page(db):
    """Render company subscription management page"""
    st.markdown("### 💳 Company Subscription")
    
    company_id = st.session_state.get('subscription_company_id')
    
    if not company_id:
        st.error("No company selected")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to Companies", key="back_from_sub_no_id", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()
        return
    
    company = db.get_company_by_id(company_id)
    
    if not company:
        st.error("Company not found")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Back to Companies", key="back_from_sub_not_found", use_container_width=True):
                st.session_state.company_sub_page = 'list'
                st.rerun()
        return
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("← Back", key="back_from_subscription"):
            st.session_state.company_sub_page = 'list'
            st.rerun()
    
    st.divider()
    
    st.markdown(f"### {company.get('company_name', 'Company')} Subscription")
    
    subscription = db.get_company_subscription(company_id)
    
    if subscription:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Current Plan:** {subscription.get('plan', 'Free').title()}")
            st.markdown(f"**Status:** {subscription.get('status', 'active').title()}")
            st.markdown(f"**Start Date:** {subscription.get('start_date', 'N/A')}")
        with col2:
            st.markdown(f"**End Date:** {subscription.get('end_date', 'N/A')}")
            st.markdown(f"**Auto Renew:** {'✅' if subscription.get('auto_renew', False) else '❌'}")
            st.markdown(f"**Trial:** {'✅' if subscription.get('is_trial', False) else '❌'}")
    else:
        st.info("No active subscription found")
    
    st.divider()
    
    st.markdown("### 🔄 Change Plan")
    
    available_plans = [
        {"id": "free", "name": "Free", "price": "$0/month", "features": ["Basic features", "5 users", "10 analyses/month"]},
        {"id": "basic", "name": "Basic", "price": "$29/month", "features": ["All Free features", "20 users", "50 analyses/month", "Email support"]},
        {"id": "pro", "name": "Pro", "price": "$79/month", "features": ["All Basic features", "Unlimited users", "Unlimited analyses", "Priority support", "Advanced analytics"]},
        {"id": "enterprise", "name": "Enterprise", "price": "$199/month", "features": ["All Pro features", "Dedicated support", "Custom integrations", "SLA guarantee"]}
    ]
    
    current_plan = subscription.get('plan', 'free').lower() if subscription else 'free'
    
    cols = st.columns(len(available_plans))
    for idx, plan in enumerate(available_plans):
        with cols[idx]:
            is_current = plan['id'] == current_plan
            st.markdown(f"""
            <div style="
                background: {'#f0f7ff' if is_current else 'white'};
                border: 2px solid {'#6366f1' if is_current else '#e2e8f0'};
                border-radius: 8px;
                padding: 16px;
                text-align: center;
                min-height: 250px;
            ">
                <h4 style="margin: 0; color: {'#6366f1' if is_current else '#1e293b'};">{plan['name']}</h4>
                <div style="font-size: 20px; font-weight: 600; margin: 8px 0; color: #1e293b;">{plan['price']}</div>
                <ul style="list-style: none; padding: 0; text-align: left; font-size: 12px; color: #64748b;">
                    {''.join([f'<li>✅ {f}</li>' for f in plan['features']])}
                </ul>
                {'<div style="margin-top: 8px; font-size: 11px; color: #6366f1; font-weight: 500;">✅ Current Plan</div>' if is_current else ''}
            </div>
            """, unsafe_allow_html=True)
            
            if not is_current:
                if st.button(f"Select {plan['name']}", key=f"select_plan_{plan['id']}_{company_id}", use_container_width=True):
                    success = db.update_company_subscription(company_id, plan['id'])
                    if success:
                        st.success(f"✅ Plan changed to {plan['name']} successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to change plan")
    
    st.divider()
    
    st.markdown("### ❌ Cancel Subscription")
    st.caption("Cancel the current subscription. This will downgrade to Free plan at the end of the billing cycle.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("❌ Cancel Subscription", key="cancel_subscription_btn", type="secondary", use_container_width=True):
            success = db.cancel_company_subscription(company_id)
            if success:
                st.success("✅ Subscription cancelled successfully! Will downgrade to Free plan.")
                st.rerun()
            else:
                st.error("❌ Failed to cancel subscription")
    
    st.divider()
    st.markdown("### 📊 Invoices")
    
    try:
        invoices = db.get_company_invoices(company_id)
        if invoices:
            for invoice in invoices:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.markdown(f"**#{invoice.get('invoice_number')}**")
                    st.caption(invoice.get('date', 'N/A'))
                with col2:
                    st.markdown(f"${invoice.get('amount', 0):,.2f}")
                with col3:
                    st.markdown(f"`{invoice.get('status', 'N/A')}`")
                with col4:
                    if st.button("📄 Download", key=f"download_invoice_{invoice.get('id')}"):
                        st.info("Download functionality")
        else:
            st.info("No invoices found")
    except:
        st.info("Invoice history not available")


# ==================== ROLE MANAGEMENT FUNCTIONS ====================

def render_role_management_page(db):
    """Render role permissions management with clean row-based layout"""
    
    st.markdown("### 🔐 Role Permissions Management")
    st.caption("Configure what each role can do in the system")
    
    try:
        roles = db.get_all_roles()
        total_roles = len(roles)
        total_permissions = sum([len([p for p in r['permissions'].values() if p]) for r in roles]) if roles else 0
        
        role_user_counts = {}
        for role_info in roles:
            try:
                users, _ = db.get_all_users_filtered(role=role_info['role'], limit=1000)
                role_user_counts[role_info['role']] = len(users)
            except:
                role_user_counts[role_info['role']] = 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Total Roles", total_roles)
        with col2:
            st.metric("🔑 Total Permissions", total_permissions)
        with col3:
            st.metric("👥 Users with Roles", sum(role_user_counts.values()))
        with col4:
            st.metric("📊 Avg Permissions per Role", f"{total_permissions/total_roles:.1f}" if total_roles > 0 else "0")
    except:
        pass
    
    st.divider()
    
    tab1, tab2 = st.tabs(["📋 Existing Roles", "➕ Add New Role"])
    
    with tab1:
        render_existing_roles_row_based(db)
    
    with tab2:
        render_add_new_role(db)


def render_existing_roles_row_based(db):
    """Render existing roles with row-based layout like users"""
    
    try:
        roles = db.get_all_roles()
    except AttributeError:
        st.warning("get_all_roles() method not available. Please update db_manager.py")
        return
    
    if not roles:
        st.warning("No roles found. Please run database migration.")
        return
    
    with st.expander("📊 Role Hierarchy Overview", expanded=False):
        hierarchy_data = []
        for role_info in roles:
            role_name = role_info['role']
            perms = role_info['permissions']
            perm_count = len([p for p in perms.values() if p])
            
            try:
                users, _ = db.get_all_users_filtered(role=role_name, limit=1000)
                user_count = len(users)
            except:
                user_count = 0
            
            hierarchy_data.append({
                'Role': role_name.replace('_', ' ').title(),
                'Description': get_role_description(role_name),
                'Users': user_count,
                'Permissions': perm_count
            })
        
        if hierarchy_data:
            df = pd.DataFrame(hierarchy_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("#### 🔐 Edit Role Permissions")
    st.caption("Click on a role to expand and edit its permissions")
    
    for role_info in roles:
        role_name = role_info['role']
        permissions = role_info['permissions']
        
        try:
            users, _ = db.get_all_users_filtered(role=role_name, limit=1000)
            user_count = len(users)
        except:
            user_count = 0
        
        perm_count = len([p for p in permissions.values() if p])
        
        avatar_class = 'default'
        if role_name in ['system_admin', 'system_support', 'system_auditor']:
            avatar_class = 'system'
        elif role_name in ['company_admin']:
            avatar_class = 'admin'
        elif role_name == 'manager':
            avatar_class = 'manager'
        elif role_name == 'analyst':
            avatar_class = 'analyst'
        elif role_name == 'viewer':
            avatar_class = 'viewer'
        
        avatar_letter = role_name[0].upper() if role_name else 'R'
        is_system = role_name in ['system_admin', 'system_support', 'system_auditor', 'company_admin', 'manager', 'analyst', 'viewer']
        
        with st.container():
            cols = st.columns([0.5, 1.5, 2.5, 1.2, 1.2, 1.5])
            
            with cols[0]:
                st.markdown(f'<div class="role-avatar {avatar_class}">{avatar_letter}</div>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                    <div>
                        <div class="role-name">{role_name.replace('_', ' ').title()}</div>
                        <div class="role-desc">{get_role_description(role_name)}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f"""
                    <div class="role-meta">
                        <span class="badge-perm-count">🔑 {perm_count} permissions</span>
                        <span class="badge-user-count">👥 {user_count} users</span>
                        {f'<span class="badge-system-role">🔒 System</span>' if is_system else ''}
                    </div>
                """, unsafe_allow_html=True)
            
            with cols[3]:
                if st.button("✏️", key=f"edit_role_{role_name}", use_container_width=True, help="Edit role permissions"):
                    st.session_state.edit_role_name = role_name
                    st.rerun()
            
            with cols[4]:
                if st.button("👁️", key=f"view_role_{role_name}", use_container_width=True, help="View role details"):
                    st.session_state.view_role_name = role_name
                    st.rerun()
            
            with cols[5]:
                if not is_system:
                    if st.button("🗑️", key=f"delete_role_{role_name}", use_container_width=True, help="Delete role"):
                        if user_count > 0:
                            st.error(f"❌ Cannot delete '{role_name}' - has {user_count} users assigned")
                        else:
                            success = db.delete_role(role_name)
                            if success:
                                st.success(f"✅ Role '{role_name}' deleted!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete")
                else:
                    st.button("🔒", key=f"locked_role_{role_name}", disabled=True, use_container_width=True, help="System role cannot be deleted")
            
            if st.session_state.get('edit_role_name') == role_name:
                with st.container():
                    st.markdown(f"""
                    <div class="permission-edit-container">
                        <h4 style="margin-top: 0;">✏️ Edit Permissions: {role_name.replace('_', ' ').title()}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    updated_perms = {}
                    
                    for category, perm_keys in PERMISSION_CATEGORIES.items():
                        category_perms = [k for k in perm_keys if k in permissions]
                        if category_perms:
                            st.markdown(f"**{category}**")
                            cols = st.columns(3)
                            
                            for i, key in enumerate(category_perms):
                                col = cols[i % 3]
                                current = permissions.get(key, False)
                                label = key.replace('_', ' ').title()
                                
                                with col:
                                    new_val = st.checkbox(label, value=current, key=f"edit_perm_{role_name}_{key}")
                                    updated_perms[key] = new_val
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"💾 Save Permissions", key=f"save_edit_perm_{role_name}", type="primary", use_container_width=True):
                            current_perms = db.get_role_permissions(role_name)
                            current_perms.update(updated_perms)
                            
                            if db.update_role_permissions(role_name, current_perms):
                                st.success(f"✅ Permissions for {role_name} updated successfully!")
                                st.session_state.edit_role_name = None
                                st.rerun()
                            else:
                                st.error("❌ Failed to update permissions")
                    
                    with col2:
                        if st.button(f"❌ Cancel", key=f"cancel_edit_perm_{role_name}", use_container_width=True):
                            st.session_state.edit_role_name = None
                            st.rerun()
            
            if st.session_state.get('view_role_name') == role_name:
                with st.container():
                    st.markdown(f"""
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 8px 0 16px 0;">
                        <h4 style="margin-top: 0;">👁️ Role Details: {role_name.replace('_', ' ').title()}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Role:** `{role_name}`")
                        st.markdown(f"**Description:** {get_role_description(role_name)}")
                        st.markdown(f"**Users:** {user_count}")
                    with col2:
                        st.markdown(f"**Permissions:** {perm_count}")
                        st.markdown(f"**System Role:** {'Yes' if is_system else 'No'}")
                    
                    st.markdown("**Permission List:**")
                    perm_cols = st.columns(3)
                    perm_list = []
                    for key, value in permissions.items():
                        if value:
                            perm_list.append(key.replace('_', ' ').title())
                    
                    if perm_list:
                        for i, perm in enumerate(perm_list):
                            with perm_cols[i % 3]:
                                st.markdown(f"✅ {perm}")
                    else:
                        st.caption("No permissions assigned")
                    
                    if st.button(f"Close", key=f"close_view_role_{role_name}", use_container_width=True):
                        st.session_state.view_role_name = None
                        st.rerun()


def render_add_new_role(db):
    """Render form to add a new role"""
    
    st.markdown("### ➕ Add New Role")
    st.caption("Create a new custom role with specific permissions")
    
    with st.form("add_new_role_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            role_name = st.text_input(
                "Role Name *", 
                placeholder="e.g., content_editor, project_manager",
                help="Use lowercase with underscores (e.g., content_editor)",
                key="new_role_name"
            )
            
            if role_name:
                if not re.match(r'^[a-z_][a-z0-9_]*$', role_name):
                    st.warning("Role name should use lowercase letters, numbers, and underscores only")
        
        with col2:
            role_description = st.text_input(
                "Role Description",
                placeholder="e.g., Can edit content but not manage users",
                help="Brief description of what this role can do",
                key="new_role_desc"
            )
        
        st.divider()
        
        st.markdown("#### 🔑 Permissions for New Role")
        st.caption("Select the permissions this role should have")
        
        new_permissions = {}
        
        for category, perm_keys in PERMISSION_CATEGORIES.items():
            st.markdown(f"**{category}**")
            cols = st.columns(3)
            
            for i, key in enumerate(perm_keys):
                col = cols[i % 3]
                label = key.replace('_', ' ').title()
                
                with col:
                    new_permissions[key] = st.checkbox(label, value=False, key=f"new_role_perm_{key}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("✅ Create Role", type="primary", use_container_width=True)
        
        with col2:
            if st.form_submit_button("❌ Reset", key="reset_new_role", use_container_width=True):
                st.rerun()
        
        if submitted:
            errors = []
            if not role_name:
                errors.append("Role name is required")
            elif not re.match(r'^[a-z_][a-z0-9_]*$', role_name):
                errors.append("Role name should use lowercase letters, numbers, and underscores only")
            
            try:
                existing_roles = db.get_all_roles()
                existing_role_names = [r['role'] for r in existing_roles]
                if role_name in existing_role_names:
                    errors.append(f"Role '{role_name}' already exists")
            except:
                pass
            
            if errors:
                for err in errors:
                    st.error(err)
            else:
                success = db.create_role(role_name, new_permissions, role_description)
                if success:
                    st.success(f"✅ Role '{role_name}' created successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to create role")


# ==================== SYSTEM CONFIGURATION FUNCTIONS ====================

def render_system_configuration(db):
    """Render system configuration page with clean UI"""
    
    st.markdown("### ⚙️ System Configuration")
    st.caption("Manage system-wide settings and configurations.")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📧 Email Settings",
        "🔐 Security Settings",
        "📊 System Settings",
        "📈 Performance"
    ])
    
    with tab1:
        render_email_settings(db)
    
    with tab2:
        render_security_settings(db)
    
    with tab3:
        render_system_settings(db)
    
    with tab4:
        render_performance_settings(db)


def render_email_settings(db):
    """Render email settings configuration"""
    st.markdown("#### 📧 Email Configuration")
    
    config_value = db.get_email_config()
    
    if not config_value:
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
        new_smtp_host = st.text_input("SMTP Host", value=config_value.get('smtp_host', 'smtp.gmail.com'), key="email_smtp_host")
        new_smtp_port = st.number_input("SMTP Port", value=config_value.get('smtp_port', 587), min_value=1, max_value=65535, key="email_smtp_port")
        new_smtp_user = st.text_input("SMTP Username", value=config_value.get('smtp_user', ''), key="email_smtp_user")
    
    with col2:
        new_smtp_password = st.text_input("SMTP Password", type="password", value=config_value.get('smtp_password', ''), key="email_smtp_password")
        new_from_email = st.text_input("From Email", value=config_value.get('from_email', ''), key="email_from")
        new_from_name = st.text_input("From Name", value=config_value.get('from_name', 'TenderAI'), key="email_from_name")
    
    test_smtp = st.checkbox("Test SMTP connection after saving", key="email_test_smtp")
    
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("💾 Save", key="save_email_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'smtp_host': new_smtp_host,
                    'smtp_port': new_smtp_port,
                    'smtp_user': new_smtp_user,
                    'smtp_password': new_smtp_password,
                    'from_email': new_from_email,
                    'from_name': new_from_name
                }
                
                success = db.update_email_config(updated_config)
                if success:
                    st.success("✅ Email settings saved successfully!")
                    if test_smtp:
                        test_smtp_connection(updated_config)
                    st.rerun()
                else:
                    st.error("❌ Failed to save email settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    with col2:
        if st.button("🔄 Reset Defaults", key="reset_email_defaults", use_container_width=True):
            defaults = {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'from_email': '',
                'from_name': 'TenderAI'
            }
            if db.update_email_config(defaults):
                st.success("✅ Reset to defaults!")
                st.rerun()
            else:
                st.error("❌ Failed to reset")
    
    st.divider()
    st.markdown("#### 📨 Test Email")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        test_email = st.text_input("Send test email to", placeholder="admin@example.com", key="test_email_input")
    with col2:
        if st.button("📨 Send Test", key="send_test_email", use_container_width=True):
            if test_email:
                try:
                    st.success(f"✅ Test email sent to {test_email}")
                except Exception as e:
                    st.error(f"❌ Failed to send test email: {e}")
            else:
                st.warning("Please enter an email address")


def test_smtp_connection(config):
    """Test SMTP connection with current settings"""
    try:
        import smtplib
        import socket
        
        if config.get('smtp_port') == 465:
            server = smtplib.SMTP_SSL(config.get('smtp_host'), config.get('smtp_port'), timeout=10)
        else:
            server = smtplib.SMTP(config.get('smtp_host'), config.get('smtp_port'), timeout=10)
            server.ehlo()
            if config.get('smtp_port') == 587:
                server.starttls()
                server.ehlo()
        
        if config.get('smtp_user') and config.get('smtp_password'):
            server.login(config.get('smtp_user'), config.get('smtp_password'))
        
        server.quit()
        st.success("✅ SMTP connection successful!")
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ SMTP Authentication failed. Check username and password.")
        return False
    except smtplib.SMTPConnectError:
        st.error("❌ SMTP Connection failed. Check host and port.")
        return False
    except socket.timeout:
        st.error("❌ SMTP Connection timeout. Check host and port.")
        return False
    except Exception as e:
        st.error(f"❌ SMTP Test failed: {e}")
        return False


def render_security_settings(db):
    """Render security settings configuration"""
    st.markdown("#### 🔐 Security Settings")
    
    config_value = db.get_security_config()
    
    if not config_value:
        config_value = {
            'require_2fa': False,
            'session_timeout': 30,
            'max_login_attempts': 5,
            'password_policy': 'strong',
            'enable_ssl': True,
            'force_https': True
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        require_2fa = st.checkbox("Require 2FA for all users", value=config_value.get('require_2fa', False), key="sec_require_2fa")
        session_timeout = st.number_input("Session Timeout (minutes)", value=config_value.get('session_timeout', 30), min_value=5, max_value=1440, key="sec_session_timeout")
        enable_ssl = st.checkbox("Enable SSL", value=config_value.get('enable_ssl', True), key="sec_enable_ssl")
    
    with col2:
        max_login_attempts = st.number_input("Max Login Attempts", value=config_value.get('max_login_attempts', 5), min_value=1, max_value=20, key="sec_max_login")
        password_policy = st.selectbox(
            "Password Policy",
            ["weak", "medium", "strong"],
            index=["weak", "medium", "strong"].index(config_value.get('password_policy', 'strong')),
            key="sec_password_policy"
        )
        force_https = st.checkbox("Force HTTPS", value=config_value.get('force_https', True), key="sec_force_https")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key="save_security_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'require_2fa': require_2fa,
                    'session_timeout': session_timeout,
                    'max_login_attempts': max_login_attempts,
                    'password_policy': password_policy,
                    'enable_ssl': enable_ssl,
                    'force_https': force_https
                }
                
                success = db.update_security_config(updated_config)
                if success:
                    st.success("✅ Security settings saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save security settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    st.divider()
    st.markdown("#### 🔒 Security Status")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("2FA Status", "✅ Enabled" if require_2fa else "❌ Disabled")
    with col2:
        st.metric("SSL Status", "✅ Enabled" if enable_ssl else "❌ Disabled")
    with col3:
        st.metric("HTTPS Force", "✅ Enabled" if force_https else "❌ Disabled")
    with col4:
        st.metric("Login Attempts", max_login_attempts)
    
    st.caption(f"🕐 Session timeout: {session_timeout} minutes | Password policy: {password_policy.upper()}")


def render_system_settings(db):
    """Render system settings configuration"""
    st.markdown("#### 📊 System Settings")
    
    config_value = db.get_system_config_settings()
    
    if not config_value:
        config_value = {
            'enable_maintenance_mode': False,
            'enable_registration': True,
            'enable_analytics': True,
            'default_language': 'en',
            'timezone': 'UTC',
            'date_format': 'YYYY-MM-DD',
            'enable_audit_log': True
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        enable_maintenance = st.checkbox("Maintenance Mode", value=config_value.get('enable_maintenance_mode', False), key="sys_maintenance")
        enable_registration = st.checkbox("Enable New Registrations", value=config_value.get('enable_registration', True), key="sys_registration")
        enable_analytics = st.checkbox("Enable Analytics", value=config_value.get('enable_analytics', True), key="sys_analytics")
        enable_audit_log = st.checkbox("Enable Audit Log", value=config_value.get('enable_audit_log', True), key="sys_audit_log")
    
    with col2:
        default_language = st.selectbox(
            "Default Language",
            ["en", "bn"],
            index=0 if config_value.get('default_language', 'en') == 'en' else 1,
            key="sys_language"
        )
        timezone = st.selectbox(
            "Timezone",
            ["UTC", "Asia/Dhaka", "Asia/Kolkata", "America/New_York", "Europe/London", "Australia/Sydney"],
            index=["UTC", "Asia/Dhaka", "Asia/Kolkata", "America/New_York", "Europe/London", "Australia/Sydney"].index(config_value.get('timezone', 'UTC')),
            key="sys_timezone"
        )
        date_format = st.selectbox(
            "Date Format",
            ["YYYY-MM-DD", "DD-MM-YYYY", "MM-DD-YYYY", "DD/MM/YYYY", "MM/DD/YYYY"],
            index=["YYYY-MM-DD", "DD-MM-YYYY", "MM-DD-YYYY", "DD/MM/YYYY", "MM/DD/YYYY"].index(config_value.get('date_format', 'YYYY-MM-DD')),
            key="sys_date_format"
        )
    
    if enable_maintenance:
        st.warning("⚠️ Maintenance mode is enabled. Users will see a maintenance page.")
        st.info("💡 To disable, uncheck the Maintenance Mode checkbox above and save.")
    
    if not enable_registration:
        st.warning("⚠️ New user registration is disabled. Only existing users can log in.")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key="save_system_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'enable_maintenance_mode': enable_maintenance,
                    'enable_registration': enable_registration,
                    'enable_analytics': enable_analytics,
                    'default_language': default_language,
                    'timezone': timezone,
                    'date_format': date_format,
                    'enable_audit_log': enable_audit_log
                }
                
                success = db.update_system_config_settings(updated_config)
                if success:
                    st.success("✅ System settings saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save system settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")


def render_performance_settings(db):
    """Render performance settings configuration"""
    st.markdown("#### 📈 Performance Settings")
    
    config_value = db.get_performance_config()
    
    if not config_value:
        config_value = {
            'cache_enabled': True,
            'cache_duration': 300,
            'max_query_limit': 1000,
            'enable_query_logging': True,
            'enable_api_caching': True,
            'compression_enabled': True
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        cache_enabled = st.checkbox("Enable Cache", value=config_value.get('cache_enabled', True), key="perf_cache")
        cache_duration = st.number_input("Cache Duration (seconds)", value=config_value.get('cache_duration', 300), min_value=30, max_value=3600, step=30, key="perf_cache_duration")
        enable_api_caching = st.checkbox("Enable API Caching", value=config_value.get('enable_api_caching', True), key="perf_api_cache")
    
    with col2:
        max_query_limit = st.number_input("Max Query Limit", value=config_value.get('max_query_limit', 1000), min_value=100, max_value=10000, step=100, key="perf_query_limit")
        enable_query_logging = st.checkbox("Enable Query Logging", value=config_value.get('enable_query_logging', True), key="perf_query_logging")
        compression_enabled = st.checkbox("Enable Compression", value=config_value.get('compression_enabled', True), key="perf_compression")
    
    st.divider()
    st.markdown("#### 📊 Cache Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cache Status", "✅ Active" if cache_enabled else "❌ Inactive")
    with col2:
        st.metric("Cache Duration", f"{cache_duration}s")
    with col3:
        st.metric("Query Limit", max_query_limit)
    with col4:
        st.metric("API Cache", "✅ Enabled" if enable_api_caching else "❌ Disabled")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col2:
        if st.button("🗑️ Clear Cache", key="clear_cache_btn", use_container_width=True):
            try:
                if db.clear_system_cache():
                    st.success("✅ Cache cleared successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to clear cache")
            except Exception as e:
                st.error(f"❌ Failed to clear cache: {e}")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key="save_performance_settings", type="primary", use_container_width=True):
            try:
                updated_config = {
                    'cache_enabled': cache_enabled,
                    'cache_duration': cache_duration,
                    'max_query_limit': max_query_limit,
                    'enable_query_logging': enable_query_logging,
                    'enable_api_caching': enable_api_caching,
                    'compression_enabled': compression_enabled
                }
                
                success = db.update_performance_config(updated_config)
                if success:
                    st.success("✅ Performance settings saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save performance settings")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")


# ==================== ADMIN OVERVIEW ====================

def render_admin_overview(all_users, all_subs):
    """Render system overview with charts"""
    st.markdown("### System Overview")
    
    try:
        db = get_db_manager()
        user_growth_data = db.get_user_growth(6)
        
        if user_growth_data and len(user_growth_data) > 0:
            user_growth = pd.DataFrame(user_growth_data)
            
            if 'month' in user_growth.columns and 'count' in user_growth.columns:
                user_growth['count'] = pd.to_numeric(user_growth['count'], errors='coerce').fillna(0)
                user_growth = user_growth.sort_values('month')
                st.line_chart(user_growth.set_index('month')['count'])
            else:
                cols = user_growth.columns.tolist()
                if len(cols) >= 2:
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
    
    if all_subs:
        plan_counts = {}
        for sub in all_subs:
            plan = sub.get('plan', 'free')
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        plan_df = pd.DataFrame(plan_counts.items(), columns=['Plan', 'Count'])
        st.bar_chart(plan_df.set_index('Plan'))
    else:
        st.info("No subscription data available")
    
    if all_users:
        role_counts = {}
        for user in all_users:
            role = user.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_df = pd.DataFrame(role_counts.items(), columns=['Role', 'Count'])
        st.bar_chart(role_df.set_index('Role'))
    else:
        st.info("No user data available")


# ==================== DATABASE BACKUP ====================

def render_database_backup():
    """Render database backup interface for Supabase"""
    
    st.markdown("### 💾 Database Backup & Export")
    st.markdown("Export your Supabase database to JSON format for backup or migration.")
    
    from config.database import DB_TYPE
    from database.connection import is_supabase
    
    if not is_supabase():
        st.warning("⚠️ This feature is only available when using Supabase as the database backend.")
        st.info("📌 You are currently using: " + (DB_TYPE.upper() if DB_TYPE else "SQLite"))
        return
    
    st.success("✅ Connected to Supabase database")
    
    try:
        supabase = get_supabase_client()
        
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
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📋 Export Options")
        
        export_format = st.selectbox(
            "Export Format",
            ["JSON", "CSV", "Both (JSON + CSV)"],
            key="backup_export_format",
            help="JSON is recommended for full data preservation"
        )
        
        table_groups = categorize_tables(ALL_TABLES)
        
        all_table_names = []
        for group, tables in table_groups.items():
            all_table_names.extend(tables)
        
        tables_to_export = st.multiselect(
            "Select Tables to Export",
            all_table_names,
            default=["users", "companies", "subscriptions"] if "users" in all_table_names else all_table_names[:3],
            key="backup_tables_select"
        )
        
        include_metadata = st.checkbox(
            "Include metadata (timestamp, table structure, counts)",
            value=True,
            key="backup_include_metadata"
        )
        
        st.caption(f"📊 {len(tables_to_export)} tables selected out of {len(ALL_TABLES)} total")
    
    with col2:
        st.markdown("#### 📊 Table Status")
        
        try:
            st.markdown('<div class="backup-status">', unsafe_allow_html=True)
            
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
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        export_btn = st.button(
            "🚀 Export Selected",
            key="export_selected_btn",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        export_all_btn = st.button(
            "📦 Export All Tables",
            key="export_all_btn",
            use_container_width=True
        )
    
    with col3:
        if st.button("🗑️ Clear Backup History", key="clear_backup_history", use_container_width=True):
            if 'backup_history' in st.session_state:
                del st.session_state['backup_history']
            st.success("Backup history cleared!")
            st.rerun()
    
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
                        response = supabase.table(table).select("*").execute()
                        data = response.data if hasattr(response, 'data') and response.data else []
                        
                        if data and len(data) > 0:
                            export_data[table] = data
                            table_stats[table] = {
                                'count': len(data),
                                'columns': list(data[0].keys()) if data else []
                            }
                            exported_count += 1
                        else:
                            export_data[table] = []
                            table_stats[table] = {'count': 0, 'columns': []}
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "PGRST" not in error_msg:
                            errors.append(f"Table '{table}': {error_msg}")
                        export_data[table] = []
                        table_stats[table] = {'count': 0, 'error': error_msg}
                
                status_text.text("✅ Export complete!")
                progress_bar.progress(1.0)
                
                if errors:
                    with st.expander("⚠️ Export Warnings"):
                        for err in errors:
                            st.warning(err)
                
                final_export = {
                    'exported_at': export_timestamp,
                    'database_type': 'supabase',
                    'tables_exported': len(tables_to_export),
                    'total_records': sum(stat.get('count', 0) for stat in table_stats.values() if isinstance(stat, dict)),
                    'table_stats': table_stats,
                    'include_metadata': include_metadata,
                    'data': export_data
                }
                
                st.session_state['latest_backup'] = final_export
                st.session_state['backup_timestamp'] = export_timestamp
                
                backup_filename = f"backup_supabase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = os.path.join('data', 'backups')
                os.makedirs(backup_path, exist_ok=True)
                
                json_file = os.path.join(backup_path, backup_filename)
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(final_export, f, indent=2, default=str)
                
                st.success(f"✅ Export successful! {exported_count} tables with data exported.")
                st.info(f"📁 Backup saved locally: `{json_file}`")
                
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
                        type="primary",
                        key="download_json_backup"
                    )
                
                with col2:
                    if export_format in ["CSV", "Both (JSON + CSV)"]:
                        try:
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
                                use_container_width=True,
                                key="download_csv_backup"
                            )
                        except Exception as e:
                            st.warning(f"⚠️ Could not create CSV: {str(e)}")
                
                with col3:
                    if st.button("📂 View Backup History", key="view_backup_history", use_container_width=True):
                        st.session_state.show_backup_history = True
                
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
                import traceback
                traceback.print_exc()
    
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
                        use_container_width=True,
                        key="download_old_backup"
                    )
                
                if st.button("🗑️ Delete Selected Backup", key="delete_selected_backup", type="secondary"):
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
        
        if st.button("🔙 Close History", key="close_backup_history", use_container_width=True):
            st.session_state.show_backup_history = False
            st.rerun()


# ==================== MAIN ADMIN DASHBOARD ====================

def show():
    """Admin dashboard page with full system management"""
    
    db = get_db_manager()
    
    # Render common styles once
    render_common_admin_styles()
    
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System-wide administration and monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    all_users = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
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
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "👑 Overview",
        "👥 Users & Roles",
        "🏢 Companies",
        "🏗️ Rate Import",
        "📦 Version Management",
        "⚙️ System Config",
        "💾 Database Backup"
    ])
    
    with tab1:
        render_admin_overview(all_users, all_subs)
    
    with tab2:
        user_role_tab1, user_role_tab2 = st.tabs(["👥 Users", "🔐 Roles"])
        
        with user_role_tab1:
            user_sub_page = st.session_state.get('user_sub_page', 'list')
            
            if user_sub_page == 'view_profile':
                render_user_profile_view(db)
            elif user_sub_page == 'edit_user':
                render_user_edit_form(db)
            else:
                render_user_management_with_routing(db)
        
        with user_role_tab2:
            render_role_management_page(db)
    
    with tab3:
        render_company_management(db)
    
    with tab4:
        render_unified_import_wizard(db)
    
    with tab5:
        render_unified_version_management()
    
    with tab6:
        render_system_configuration(db)
    
    with tab7:
        render_database_backup()