# modules/unified_version_manager.py - Refactored without wrapper class

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from database.unified_db_manager import get_db_manager


def render_unified_version_management(db=None):
    """Render unified version management UI"""
    
    if db is None:
        db = get_db_manager()
    
    st.markdown("### 📅 Unified Rate Schedule Version Management")
    st.caption("Manage both PWD and LGED rate schedule versions")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs([
        "📊 Active Versions",
        "📜 Version History",
        "📈 Version Comparison"
    ])
    
    with tab1:
        render_active_versions(db)
    
    with tab2:
        render_version_history(db)
    
    with tab3:
        render_version_comparison(db)


def render_active_versions(db):
    """Show currently active versions"""
    
    st.markdown("#### ✅ Currently Active Versions")
    if db is None:
        db = get_db_manager() 
    # ✅ Use db directly
    

    active_versions = db.get_active_version()
    
    if not active_versions:
        st.info("No active versions. Please import a rate schedule and activate it.")
    else:
        for version in active_versions:
            source = version.get('source')
            icon = "🏗️" if source == 'PWD' else "🛣️"
            
            with st.expander(f"{icon} {source} - {version.get('version_name')} ({version.get('edition_year')})", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Edition Year", version.get('edition_year', 'N/A'))
                with col2:
                    st.metric("Status", "✅ Active")
                with col3:
                    st.metric("Effective From", version.get('effective_from') if version.get('effective_from') else 'N/A')
                with col4:
                    release_date = version.get('release_date', '')
                    st.metric("Released", release_date[:10] if release_date else 'N/A')
                
                # Get detailed stats
                stats = db.get_version_stats(version.get('id'))
                if stats:
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Parents", stats.get('parents', 0))
                    col_b.metric("Children", stats.get('children', 0))
                    col_c.metric("Rate Entries", stats.get('rates', 0))
                
                if version.get('notes'):
                    st.caption(f"📝 Notes: {version.get('notes')}")
    
    st.markdown("---")
    st.markdown("#### 📊 Version Summary")
    
    # ✅ Use db directly
    all_versions = db.get_all_versions()
    
    if all_versions:
        # Group by source and calculate counts
        summary_data = {}
        for version in all_versions:
            source = version.get('source')
            if source not in summary_data:
                summary_data[source] = {'total': 0, 'active': 0}
            summary_data[source]['total'] += 1
            if version.get('is_active'):
                summary_data[source]['active'] += 1
        
        summary_df = pd.DataFrame([
            {'Source': k, 'Total Versions': v['total'], 'Active Versions': v['active']}
            for k, v in summary_data.items()
        ])
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

def render_version_history(db):
    """Show complete version history for both PWD and LGED"""
    
    st.markdown("#### 📜 Complete Version History")
    if db is None:
        db = get_db_manager()
    # Filter by source
    source_filter = st.selectbox(
        "Filter by Source",
        options=["All", "PWD", "LGED"]
    )
    
    # Use db directly
    if source_filter == "All":
        versions = db.get_all_versions()
    else:
        versions = db.get_all_versions(source=source_filter)
    
    if not versions:
        st.info("No versions found. Import a rate schedule first.")
        return
    
    # ✅ Helper function to safely get value from dict or tuple
    def safe_get(item, key, default=''):
        if isinstance(item, dict):
            val = item.get(key, default)
            return val if val is not None else default
        elif isinstance(item, (list, tuple)):
            # Map keys to indices based on known order
            key_index = {
                'id': 0,
                'source': 1,
                'version_name': 2,
                'edition_year': 3,
                'effective_from': 4,
                'is_active': 5,
                'release_date': 6,
                'created_by': 7,
                'notes': 8,
                'total_parents': 9,
                'total_children': 10,
                'total_rates': 11
            }
            idx = key_index.get(key)
            if idx is not None and len(item) > idx:
                val = item[idx]
                return val if val is not None else default
            return default
        return default
    
    # Display versions in a table
    display_data = []
    for v in versions:
        display_data.append({
            'Source': safe_get(v, 'source'),
            'Version Name': safe_get(v, 'version_name'),
            'Year': safe_get(v, 'edition_year'),
            'Effective From': safe_get(v, 'effective_from'),
            'Status': "✅ Active" if safe_get(v, 'is_active', False) else "📦 Archived",
            'Released': str(safe_get(v, 'release_date', ''))[:10] if safe_get(v, 'release_date', '') else 'N/A',
            'Created By': safe_get(v, 'created_by'),
            'Notes': str(safe_get(v, 'notes', ''))[:50] + ('...' if len(str(safe_get(v, 'notes', ''))) > 50 else '')
        })
    
    st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("#### 🔧 Version Actions")
    
    # Version selection for actions
    col1, col2 = st.columns(2)
    
    with col1:
        # ✅ Create options safely
        version_options = {}
        for v in versions:
            v_id = v.get('id') if isinstance(v, dict) else v[0] if len(v) > 0 else None
            if v_id:
                source = v.get('source') if isinstance(v, dict) else v[1] if len(v) > 1 else 'Unknown'
                name = v.get('version_name') if isinstance(v, dict) else v[2] if len(v) > 2 else 'Unnamed'
                year = v.get('edition_year') if isinstance(v, dict) else v[3] if len(v) > 3 else 'N/A'
                version_options[v_id] = f"{source} - {name} ({year})"
        
        if version_options:
            version_to_activate = st.selectbox(
                "Select Version to Activate",
                options=list(version_options.keys()),
                format_func=lambda x: version_options.get(x, "Unknown")
            )
            
            if st.button("⭐ Activate Selected Version", type="primary"):
                success = db.activate_version(
                    version_to_activate, 
                    st.session_state.get('username', 'admin')
                )
                if success:
                    st.success("✅ Version activated successfully!")
                    st.rerun()
        else:
            st.info("No versions available to activate")
    
    with col2:
        # ✅ Filter active versions
        active_versions = []
        for v in versions:
            is_active = v.get('is_active') if isinstance(v, dict) else v[5] if len(v) > 5 else False
            if is_active:
                active_versions.append(v)
        
        if active_versions:
            archive_options = {}
            for v in active_versions:
                v_id = v.get('id') if isinstance(v, dict) else v[0] if len(v) > 0 else None
                if v_id:
                    source = v.get('source') if isinstance(v, dict) else v[1] if len(v) > 1 else 'Unknown'
                    name = v.get('version_name') if isinstance(v, dict) else v[2] if len(v) > 2 else 'Unnamed'
                    year = v.get('edition_year') if isinstance(v, dict) else v[3] if len(v) > 3 else 'N/A'
                    archive_options[v_id] = f"{source} - {name} ({year})"
            
            version_to_archive = st.selectbox(
                "Select Version to Archive",
                options=list(archive_options.keys()),
                format_func=lambda x: archive_options.get(x, "Unknown")
            )
            
            if st.button("📦 Archive Selected Version"):
                if version_to_archive:
                    success = db.archive_version(
                        version_to_archive,
                        st.session_state.get('username', 'admin')
                    )
                    if success:
                        st.success("✅ Version archived successfully!")
                        st.rerun()
                else:
                    st.warning("No version selected for archiving")
        else:
            st.info("No active versions available to archive")
            
def render_version_comparison(db):
    """Compare two versions side by side"""
    
    st.markdown("#### 📊 Compare Versions")
    if db is None:
        db = get_db_manager()
    # ✅ Use db directly
    all_versions = db.get_all_versions()
    
    if len(all_versions) < 2:
        st.info("Need at least 2 versions to compare")
        return
    
    # Create version lookup
    version_lookup = {v.get('id'): v for v in all_versions}
    version_options = {v.get('id'): f"{v.get('source')} - {v.get('version_name')} ({v.get('edition_year')})" 
                      for v in all_versions}
    
    col1, col2 = st.columns(2)
    
    with col1:
        version_1_id = st.selectbox(
            "Select First Version",
            options=list(version_options.keys()),
            format_func=lambda x: version_options.get(x, "Unknown"),
            key="compare_1"
        )
    
    with col2:
        version_2_id = st.selectbox(
            "Select Second Version",
            options=list(version_options.keys()),
            format_func=lambda x: version_options.get(x, "Unknown"),
            key="compare_2"
        )
    
    if version_1_id and version_2_id and version_1_id != version_2_id:
        if st.button("Compare Versions", type="primary"):
            v1 = version_lookup.get(version_1_id, {})
            v2 = version_lookup.get(version_2_id, {})
            
            # Get stats
            stats1 = db.get_version_stats(version_1_id)
            stats2 = db.get_version_stats(version_2_id)
            
            st.markdown("#### Comparison Results")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric("Source", v1.get('source', 'N/A'))
                st.metric("Version", v1.get('version_name', 'N/A'))
                st.metric("Year", v1.get('edition_year', 'N/A'))
                if stats1:
                    st.metric("Items", stats1.get('parents', 0) + stats1.get('children', 0))
            
            with col_b:
                st.metric("→", "vs")
            
            with col_c:
                st.metric("Source", v2.get('source', 'N/A'))
                st.metric("Version", v2.get('version_name', 'N/A'))
                st.metric("Year", v2.get('edition_year', 'N/A'))
                if stats2:
                    st.metric("Items", stats2.get('parents', 0) + stats2.get('children', 0))
            
            with col_d:
                if stats1 and stats2:
                    parent_diff = (stats2.get('parents', 0) - stats1.get('parents', 0))
                    child_diff = (stats2.get('children', 0) - stats1.get('children', 0))
                    st.metric("Parent Δ", f"{parent_diff:+d}")
                    st.metric("Child Δ", f"{child_diff:+d}")
            
            # Show differences if same source
            if v1.get('source') == v2.get('source'):
                st.info(f"Both versions are from {v1.get('source')}. You can view detailed item differences in the respective source viewers.")


def register_version_after_import(db, source, version_name, edition_year, effective_date, 
                                  total_parents, total_children, total_rates):
    """Call this after successful import to register the version"""
    if db is None:
        db = get_db_manager()
    # ✅ Use db directly
    version_id = db.add_version({
        'source': source,
        'version_name': version_name,
        'edition_year': edition_year,
        'effective_from': effective_date,
        'created_by': st.session_state.get('username', 'admin'),
        'notes': f"Imported {source} rate schedule",
        'total_parents': total_parents,
        'total_children': total_children,
        'total_rates': total_rates
    })
    
    return version_id