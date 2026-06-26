# modules/unified_version_manager.py

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

class UnifiedVersionManager:
    """Unified version management for both PWD and LGED rate schedules"""
    
    def __init__(self, db_instance):
        self.db = db_instance
    
    def init_unified_tables(self):
        """Initialize unified version tracking tables"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Unified versions table (tracks both PWD and LGED)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL CHECK(source IN ('PWD', 'LGED')),
                version_name TEXT NOT NULL,
                edition_year INTEGER NOT NULL,
                effective_from DATE,
                effective_to DATE,
                is_active BOOLEAN DEFAULT 0,
                released_by TEXT,
                release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                total_parents INTEGER DEFAULT 0,
                total_children INTEGER DEFAULT 0,
                total_rates INTEGER DEFAULT 0,
                created_by TEXT,
                UNIQUE(source, edition_year)
            )
        """)
        
        # Version change log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER,
                source TEXT,
                action TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_version_source ON rate_versions(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_version_active ON rate_versions(is_active)")
        
        conn.commit()
        conn.close()
        print("✅ Unified version tables initialized")
    
    def get_active_version(self, source=None):
        """Get active version for a source or all active versions"""
        conn = self.db.get_connection()
        
        if source:
            df = pd.read_sql_query("""
                SELECT * FROM rate_versions 
                WHERE source = ? AND is_active = 1
                ORDER BY edition_year DESC
                LIMIT 1
            """, conn, params=(source,))
        else:
            df = pd.read_sql_query("""
                SELECT * FROM rate_versions 
                WHERE is_active = 1
                ORDER BY source, edition_year DESC
            """, conn)
        
        conn.close()
        return df
    
    def get_all_versions(self, source=None):
        """Get all versions, optionally filtered by source"""
        conn = self.db.get_connection()
        
        if source:
            df = pd.read_sql_query("""
                SELECT * FROM rate_versions 
                WHERE source = ?
                ORDER BY edition_year DESC
            """, conn, params=(source,))
        else:
            df = pd.read_sql_query("""
                SELECT * FROM rate_versions 
                ORDER BY source, edition_year DESC
            """, conn)
        
        conn.close()
        return df
    
    def activate_version(self, version_id, activated_by):
        """Activate a specific version (deactivate others of same source)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get the source of this version
        cursor.execute("SELECT source FROM rate_versions WHERE id = ?", (version_id,))
        source = cursor.fetchone()[0]
        
        # Deactivate all versions of the same source
        cursor.execute("UPDATE rate_versions SET is_active = 0 WHERE source = ?", (source,))
        
        # Activate the selected version
        cursor.execute("""
            UPDATE rate_versions 
            SET is_active = 1, released_by = ?, release_date = ?
            WHERE id = ?
        """, (activated_by, datetime.now(), version_id))
        
        # Log the change
        cursor.execute("""
            INSERT INTO version_change_log (version_id, source, action, changed_by, details)
            VALUES (?, ?, ?, ?, ?)
        """, (version_id, source, 'activate', activated_by, f"Activated version by {activated_by}"))
        
        conn.commit()
        conn.close()
        
        return True
    
    def add_version(self, source, version_name, edition_year, effective_from, 
                    created_by, notes="", total_parents=0, total_children=0, total_rates=0):
        """Add a new version (called after successful import)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Check if version already exists
        cursor.execute("""
            SELECT id FROM rate_versions 
            WHERE source = ? AND edition_year = ?
        """, (source, edition_year))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute("""
                UPDATE rate_versions 
                SET version_name = ?, effective_from = ?, notes = ?,
                    total_parents = ?, total_children = ?, total_rates = ?,
                    release_date = ?
                WHERE id = ?
            """, (version_name, effective_from, notes, total_parents, total_children, 
                  total_rates, datetime.now(), existing[0]))
            version_id = existing[0]
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO rate_versions 
                (source, version_name, edition_year, effective_from, created_by, notes, 
                 total_parents, total_children, total_rates, release_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (source, version_name, edition_year, effective_from, created_by, notes,
                  total_parents, total_children, total_rates, datetime.now(), 0))
            version_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return version_id
    
    def archive_version(self, version_id, archived_by):
        """Archive a version (set inactive)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE rate_versions SET is_active = 0 WHERE id = ?", (version_id,))
        
        cursor.execute("""
            INSERT INTO version_change_log (version_id, source, action, changed_by, details)
            VALUES (?, (SELECT source FROM rate_versions WHERE id = ?), ?, ?, ?)
        """, (version_id, version_id, 'archive', archived_by, f"Archived version"))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_version_stats(self, version_id):
        """Get detailed statistics for a specific version"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source FROM rate_versions WHERE id = ?
        """, (version_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return None
        
        source = result[0]
        
        if source == 'PWD':
            # Query PWD tables
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM pwd_parents WHERE version_id = ?) as parents,
                    (SELECT COUNT(*) FROM pwd_children WHERE version_id = ?) as children,
                    (SELECT COUNT(*) FROM pwd_rates WHERE version_id = ?) as rates
            """, (version_id, version_id, version_id))
        else:
            # Query LGED tables
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM lged_parents WHERE version_id = ?) as parents,
                    (SELECT COUNT(*) FROM lged_children WHERE version_id = ?) as children,
                    (SELECT COUNT(*) FROM lged_zone_rates WHERE version_id = ?) as rates
            """, (version_id, version_id, version_id))
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            'parents': stats[0] or 0,
            'children': stats[1] or 0,
            'rates': stats[2] or 0
        }


def render_unified_version_management(db):
    """Render unified version management UI"""
    
    version_manager = UnifiedVersionManager(db)
    version_manager.init_unified_tables()
    
    st.markdown("### 📅 Unified Rate Schedule Version Management")
    st.caption("Manage both PWD and LGED rate schedule versions")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs([
        "📊 Active Versions",
        "📜 Version History",
        "📈 Version Comparison"
    ])
    
    with tab1:
        render_active_versions(version_manager, db)
    
    with tab2:
        render_version_history(version_manager, db)
    
    with tab3:
        render_version_comparison(version_manager, db)


def render_active_versions(version_manager, db):
    """Show currently active versions"""
    
    st.markdown("#### ✅ Currently Active Versions")
    
    active_versions = version_manager.get_active_version()
    
    if active_versions.empty:
        st.info("No active versions. Please import a rate schedule and activate it.")
    else:
        for _, version in active_versions.iterrows():
            source = version['source']
            icon = "🏗️" if source == 'PWD' else "🛣️"
            
            with st.expander(f"{icon} {source} - {version['version_name']} ({version['edition_year']})", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Edition Year", version['edition_year'])
                with col2:
                    st.metric("Status", "✅ Active")
                with col3:
                    st.metric("Effective From", version['effective_from'] if version['effective_from'] else 'N/A')
                with col4:
                    st.metric("Released", version['release_date'][:10] if version['release_date'] else 'N/A')
                
                # Get detailed stats
                stats = version_manager.get_version_stats(version['id'])
                if stats:
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Parents", stats['parents'])
                    col_b.metric("Children", stats['children'])
                    col_c.metric("Rate Entries", stats['rates'])
                
                if version['notes']:
                    st.caption(f"📝 Notes: {version['notes']}")
    
    st.markdown("---")
    st.markdown("#### 📊 Version Summary")
    
    all_versions = version_manager.get_all_versions()
    
    if not all_versions.empty:
        summary = all_versions.groupby('source').agg({
            'edition_year': 'count',
            'is_active': 'sum'
        }).rename(columns={'edition_year': 'total_versions', 'is_active': 'active_versions'})
        
        st.dataframe(summary, use_container_width=True)


def render_version_history(version_manager, db):
    """Show complete version history for both PWD and LGED"""
    
    st.markdown("#### 📜 Complete Version History")
    
    # Filter by source
    col1, col2 = st.columns(2)
    with col1:
        source_filter = st.selectbox(
            "Filter by Source",
            options=["All", "PWD", "LGED"]
        )
    
    # Get versions
    if source_filter == "All":
        versions_df = version_manager.get_all_versions()
    else:
        versions_df = version_manager.get_all_versions(source=source_filter)
    
    if versions_df.empty:
        st.info("No versions found. Import a rate schedule first.")
        return
    
    # Display versions in a table
    display_df = versions_df[[
        'source', 'version_name', 'edition_year', 'effective_from', 
        'is_active', 'release_date', 'created_by', 'notes'
    ]].copy()
    
    display_df['is_active'] = display_df['is_active'].apply(lambda x: "✅ Active" if x else "📦 Archived")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("#### 🔧 Version Actions")
    
    # Version selection for actions
    col1, col2 = st.columns(2)
    
    with col1:
        version_to_activate = st.selectbox(
            "Select Version to Activate",
            options=versions_df['id'].tolist(),
            format_func=lambda x: f"{versions_df[versions_df['id']==x]['source'].iloc[0]} - {versions_df[versions_df['id']==x]['version_name'].iloc[0]} ({versions_df[versions_df['id']==x]['edition_year'].iloc[0]})"
        )
        
        if st.button("⭐ Activate Selected Version", type="primary"):
            success = version_manager.activate_version(
                version_to_activate, 
                st.session_state.get('username', 'admin')
            )
            if success:
                st.success("✅ Version activated successfully!")
                st.rerun()
    
    with col2:
        version_to_archive = st.selectbox(
            "Select Version to Archive",
            options=versions_df[versions_df['is_active'] == True]['id'].tolist() if not versions_df[versions_df['is_active'] == True].empty else [],
            format_func=lambda x: f"{versions_df[versions_df['id']==x]['source'].iloc[0]} - {versions_df[versions_df['id']==x]['version_name'].iloc[0]}"
        )
        
        if st.button("📦 Archive Selected Version"):
            if version_to_archive:
                success = version_manager.archive_version(
                    version_to_archive,
                    st.session_state.get('username', 'admin')
                )
                if success:
                    st.success("✅ Version archived successfully!")
                    st.rerun()
            else:
                st.warning("No active version selected for archiving")


def render_version_comparison(version_manager, db):
    """Compare two versions side by side"""
    
    st.markdown("#### 📊 Compare Versions")
    
    all_versions = version_manager.get_all_versions()
    
    if len(all_versions) < 2:
        st.info("Need at least 2 versions to compare")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        version_1 = st.selectbox(
            "Select First Version",
            options=all_versions['id'].tolist(),
            format_func=lambda x: f"{all_versions[all_versions['id']==x]['source'].iloc[0]} - {all_versions[all_versions['id']==x]['version_name'].iloc[0]} ({all_versions[all_versions['id']==x]['edition_year'].iloc[0]})",
            key="compare_1"
        )
    
    with col2:
        version_2 = st.selectbox(
            "Select Second Version",
            options=all_versions['id'].tolist(),
            format_func=lambda x: f"{all_versions[all_versions['id']==x]['source'].iloc[0]} - {all_versions[all_versions['id']==x]['version_name'].iloc[0]} ({all_versions[all_versions['id']==x]['edition_year'].iloc[0]})",
            key="compare_2"
        )
    
    if version_1 and version_2 and version_1 != version_2:
        if st.button("Compare Versions", type="primary"):
            # Get version details
            v1 = all_versions[all_versions['id'] == version_1].iloc[0]
            v2 = all_versions[all_versions['id'] == version_2].iloc[0]
            
            # Get stats
            stats1 = version_manager.get_version_stats(version_1)
            stats2 = version_manager.get_version_stats(version_2)
            
            st.markdown("#### Comparison Results")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric("Source", v1['source'])
                st.metric("Version", v1['version_name'])
                st.metric("Year", v1['edition_year'])
                if stats1:
                    st.metric("Items", stats1['parents'] + stats1['children'])
            
            with col_b:
                st.metric("→", "vs")
            
            with col_c:
                st.metric("Source", v2['source'])
                st.metric("Version", v2['version_name'])
                st.metric("Year", v2['edition_year'])
                if stats2:
                    st.metric("Items", stats2['parents'] + stats2['children'])
            
            with col_d:
                if stats1 and stats2:
                    parent_diff = (stats2['parents'] - stats1['parents'])
                    child_diff = (stats2['children'] - stats1['children'])
                    st.metric("Parent Δ", f"{parent_diff:+d}")
                    st.metric("Child Δ", f"{child_diff:+d}")
            
            # Show differences if same source
            if v1['source'] == v2['source']:
                st.info(f"Both versions are from {v1['source']}. You can view detailed item differences in the respective source viewers.")


# Integration with existing PWD and LGED importers
def register_version_after_import(db, source, version_name, edition_year, effective_date, 
                                  total_parents, total_children, total_rates):
    """Call this after successful import to register the version"""
    
    version_manager = UnifiedVersionManager(db)
    version_manager.init_unified_tables()
    
    version_id = version_manager.add_version(
        source=source,
        version_name=version_name,
        edition_year=edition_year,
        effective_from=effective_date,
        created_by=st.session_state.get('username', 'admin'),
        notes=f"Imported {source} rate schedule",
        total_parents=total_parents,
        total_children=total_children,
        total_rates=total_rates
    )
    
    return version_id