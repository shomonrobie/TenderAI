"""
PWD Management Module - Import and Management
"""

import streamlit as st
import pandas as pd
import os
import datetime
from modules.pwd_data_manager import (
    PWDParserWithHierarchy,
    PWDExtractorForVerification,
    save_hierarchy_to_database,
    get_rate_versions,
    archive_version
)
from database.unified_db_manager import get_db_manager


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
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2022, key="pwd_edition_year")
    
    with col2:
        max_pages = st.number_input("Preview Pages", min_value=1, max_value=500, value=10,
                                    help="Process first N pages. Set to 500 for full PDF.",
                                    key="pwd_max_pages")
    
    dry_run = st.checkbox("🔍 Dry Run Mode (Preview only, no database save)", value=True, key="pwd_dry_run")
    
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