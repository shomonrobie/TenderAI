# modules/unified_rollback_manager.py - UPDATED VERSION

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import json


class UnifiedRollbackManager:
    """Unified rollback management for both PWD and LGED"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        # ✅ REMOVED: _init_unified_tables() - tables already exist in unified manager
    
    # ❌ DELETED: _init_unified_tables() - Not needed, tables created by unified manager
    
    def create_snapshot(self, source, version_id, snapshot_name, created_by, description="", is_auto=False):
        """Create a snapshot for PWD or LGED"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Collect current data based on source
        data = self._collect_current_data(source, version_id)
        
        cursor.execute("""
            INSERT INTO rate_snapshots (source, version_id, snapshot_name, created_by, description, data_json, is_auto)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source, version_id, snapshot_name, created_by, description, json.dumps(data), 1 if is_auto else 0))
        
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    def _collect_current_data(self, source, version_id):
        """Collect current data for snapshot based on source"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        data = {
            'parents': [],
            'children': [],
            'rates': []
        }
        
        if source == 'PWD':
            # Get PWD parents
            cursor.execute("SELECT pwd_code, description, chapter_number FROM pwd_parents WHERE version_id = ?", (version_id,))
            for row in cursor.fetchall():
                data['parents'].append({
                    'code': row[0],
                    'description': row[1],
                    'chapter_number': row[2]
                })
            
            # Get PWD children
            cursor.execute("SELECT pwd_code, parent_code, description, unit FROM pwd_children WHERE version_id = ?", (version_id,))
            for row in cursor.fetchall():
                data['children'].append({
                    'code': row[0],
                    'parent_code': row[1],
                    'description': row[2],
                    'unit': row[3]
                })
            
            # Get PWD rates
            cursor.execute("SELECT pwd_code, zone_name, unit_rate FROM pwd_rates WHERE version_id = ?", (version_id,))
            for row in cursor.fetchall():
                data['rates'].append({
                    'code': row[0],
                    'zone': row[1],
                    'rate': row[2]
                })
        
        else:  # LGED
            # Get LGED parents
            cursor.execute("SELECT code, description, chapter_number FROM lged_parents WHERE version_id = ?", (version_id,))
            for row in cursor.fetchall():
                data['parents'].append({
                    'code': row[0],
                    'description': row[1],
                    'chapter_number': row[2]
                })
            
            # Get LGED children
            cursor.execute("SELECT code, parent_code, description, unit FROM lged_children WHERE version_id = ?", (version_id,))
            for row in cursor.fetchall():
                data['children'].append({
                    'code': row[0],
                    'parent_code': row[1],
                    'description': row[2],
                    'unit': row[3]
                })
            
            # Get LGED rates
            cursor.execute("""
                SELECT c.code, r.zone_name, r.unit_rate 
                FROM lged_children c
                JOIN lged_zone_rates r ON c.id = r.child_id
                WHERE c.version_id = ?
            """, (version_id,))
            for row in cursor.fetchall():
                data['rates'].append({
                    'code': row[0],
                    'zone': row[1],
                    'rate': row[2]
                })
        
        conn.close()
        return data
    
    def rollback_to_snapshot(self, snapshot_id, rollback_by):
        """Rollback to a specific snapshot"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get snapshot data
        cursor.execute("SELECT source, version_id, data_json, snapshot_name FROM rate_snapshots WHERE id = ?", (snapshot_id,))
        snapshot = cursor.fetchone()
        
        if not snapshot:
            conn.close()
            return False, "Snapshot not found"
        
        source, version_id, data_json, snapshot_name = snapshot
        
        # Create auto-backup before rollback
        self.create_snapshot(
            source=source,
            version_id=version_id,
            snapshot_name=f"Auto-backup before rollback to {snapshot_name}",
            created_by=rollback_by,
            description="Automatic backup created before rollback",
            is_auto=True
        )
        
        # Restore data based on source
        data = json.loads(data_json)
        
        if source == 'PWD':
            # Clear existing PWD data
            cursor.execute("DELETE FROM pwd_rates WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM pwd_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM pwd_parents WHERE version_id = ?", (version_id,))
            
            # Restore PWD parents
            for parent in data['parents']:
                cursor.execute("""
                    INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                """, (parent['code'], parent['description'], parent['chapter_number'], version_id))
            
            # Restore PWD children
            for child in data['children']:
                cursor.execute("""
                    INSERT INTO pwd_children (pwd_code, parent_code, description, unit, version_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (child['code'], child['parent_code'], child['description'], child['unit'], version_id))
            
            # Restore PWD rates
            for rate in data['rates']:
                cursor.execute("""
                    INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, version_id)
                    VALUES (?, ?, ?, ?)
                """, (rate['code'], rate['zone'], rate['rate'], version_id))
        
        else:  # LGED
            # Clear existing LGED data
            cursor.execute("DELETE FROM lged_zone_rates WHERE version_id IN (SELECT id FROM lged_children WHERE version_id = ?)", (version_id,))
            cursor.execute("DELETE FROM lged_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_parents WHERE version_id = ?", (version_id,))
            
            # Restore LGED parents
            for parent in data['parents']:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                """, (parent['code'], parent['description'], parent['chapter_number'], version_id))
            
            # Restore LGED children
            for child in data['children']:
                cursor.execute("""
                    INSERT INTO lged_children (code, parent_code, description, unit, version_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (child['code'], child['parent_code'], child['description'], child['unit'], version_id))
                child_id = cursor.lastrowid
                
                # Restore LGED rates
                for rate in data['rates']:
                    if rate['code'] == child['code']:
                        cursor.execute("""
                            INSERT INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                            VALUES (?, ?, ?, ?)
                        """, (child_id, rate['zone'], rate['rate'], version_id))
        
        # Log the rollback
        cursor.execute("""
            INSERT INTO rate_change_log (source, version_id, action, changed_by, details)
            VALUES (?, ?, ?, ?, ?)
        """, (source, version_id, 'rollback', rollback_by, f"Rolled back to snapshot: {snapshot_name}"))
        
        conn.commit()
        conn.close()
        
        return True, f"Successfully rolled back to {snapshot_name}"
    
    def get_snapshots(self, source=None):
        """Get snapshots, optionally filtered by source"""
        conn = self.db.get_connection()
        
        if source:
            df = pd.read_sql_query("""
                SELECT * FROM rate_snapshots 
                WHERE source = ? 
                ORDER BY created_at DESC
            """, conn, params=(source,))
        else:
            df = pd.read_sql_query("""
                SELECT * FROM rate_snapshots 
                ORDER BY created_at DESC
                LIMIT 100
            """, conn)
        
        conn.close()
        return df
    
    def record_import(self, source, version_id, version_name, edition_year, imported_by,
                      total_parents, total_children, total_rates, notes=""):
        """Record an import in history"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rate_import_history 
            (source, version_id, version_name, edition_year, imported_by, 
             total_parents, total_children, total_rates, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (source, version_id, version_name, edition_year, imported_by,
              total_parents, total_children, total_rates, notes))
        
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return history_id
    
    def get_import_history(self, source=None):
        """Get import history, optionally filtered by source"""
        conn = self.db.get_connection()
        
        if source:
            df = pd.read_sql_query("""
                SELECT * FROM rate_import_history 
                WHERE source = ? 
                ORDER BY import_date DESC
            """, conn, params=(source,))
        else:
            df = pd.read_sql_query("""
                SELECT * FROM rate_import_history 
                ORDER BY import_date DESC
                LIMIT 50
            """, conn)
        
        conn.close()
        return df


def render_rollback_management(db):
    """Render unified rollback management tab in admin dashboard"""
    
    rollback_manager = UnifiedRollbackManager(db)
    
    st.markdown("### 🔄 Unified Rollback Management")
    st.caption("Manage rollback snapshots for both PWD and LGED rate schedules")
    
    # Tabs for different rollback views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Snapshots",
        "📜 Import History",
        "🔄 Rollback Actions",
        "💾 Create Snapshot"
    ])
    
    with tab1:
        render_snapshots_tab(rollback_manager)
    
    with tab2:
        render_import_history_tab(rollback_manager)
    
    with tab3:
        render_rollback_actions_tab(rollback_manager, db)
    
    with tab4:
        render_create_snapshot_tab(rollback_manager, db)


def render_snapshots_tab(rollback_manager):
    """Display all rollback snapshots"""
    
    st.markdown("#### 📸 Available Rollback Snapshots")
    
    # Filter by source
    col1, col2 = st.columns(2)
    with col1:
        source_filter = st.selectbox(
            "Filter by Source",
            options=["All", "PWD", "LGED"],
            key="snapshot_source_filter"
        )
    
    # Get snapshots
    if source_filter == "All":
        snapshots_df = rollback_manager.get_snapshots()
    else:
        snapshots_df = rollback_manager.get_snapshots(source=source_filter)
    
    if snapshots_df.empty:
        st.info("No snapshots found. Create one in the 'Create Snapshot' tab.")
        return
    
    # Display snapshots
    for _, snapshot in snapshots_df.iterrows():
        source_icon = "🏗️" if snapshot['source'] == 'PWD' else "🛣️"
        
        with st.expander(f"{source_icon} {snapshot['snapshot_name']} - {snapshot['created_at'][:16]}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Source:** {snapshot['source']}")
                st.write(f"**Created By:** {snapshot['created_by']}")
            with col2:
                st.write(f"**Auto Snapshot:** {'Yes' if snapshot['is_auto'] else 'No'}")
                st.write(f"**Version ID:** {snapshot['version_id']}")
            with col3:
                st.write(f"**Description:** {snapshot['description'] or 'No description'}")
            
            if st.button(f"🔄 Rollback to this snapshot", key=f"rollback_{snapshot['id']}"):
                success, message = rollback_manager.rollback_to_snapshot(
                    snapshot['id'],
                    st.session_state.get('username', 'admin')
                )
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)


def render_import_history_tab(rollback_manager):
    """Display import history"""
    
    st.markdown("#### 📜 Import History")
    
    # Filter by source
    col1, col2 = st.columns(2)
    with col1:
        source_filter = st.selectbox(
            "Filter by Source",
            options=["All", "PWD", "LGED"],
            key="history_source_filter"
        )
    
    # Get history
    if source_filter == "All":
        history_df = rollback_manager.get_import_history()
    else:
        history_df = rollback_manager.get_import_history(source=source_filter)
    
    if history_df.empty:
        st.info("No import history found")
        return
    
    # Format for display
    display_df = history_df[[
        'import_date', 'source', 'version_name', 'edition_year',
        'total_parents', 'total_children', 'total_rates', 'status'
    ]].copy()
    
    display_df = display_df.rename(columns={
        'import_date': 'Import Date',
        'source': 'Source',
        'version_name': 'Version',
        'edition_year': 'Year',
        'total_parents': 'Parents',
        'total_children': 'Children',
        'total_rates': 'Rates',
        'status': 'Status'
    })
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_rollback_actions_tab(rollback_manager, db):
    """Perform rollback actions"""
    
    st.markdown("#### 🔄 Rollback Actions")
    
    # Get active versions
    conn = db.get_connection()
    
    # PWD active version
    pwd_active = pd.read_sql_query("""
        SELECT id, version_name, edition_year FROM rate_versions 
        WHERE source = 'PWD' AND is_active = 1 
        LIMIT 1
    """, conn)
    
    # LGED active version
    lged_active = pd.read_sql_query("""
        SELECT id, version_name, edition_year FROM rate_versions 
        WHERE source = 'LGED' AND is_active = 1 
        LIMIT 1
    """, conn)
    
    conn.close()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏗️ PWD")
        if not pwd_active.empty:
            st.write(f"**Active Version:** {pwd_active.iloc[0]['version_name']} ({pwd_active.iloc[0]['edition_year']})")
            
            if st.button("📸 Create PWD Rollback Point", use_container_width=True):
                st.info("Use the 'Create Snapshot' tab to create a snapshot")
        else:
            st.info("No active PWD version")
    
    with col2:
        st.markdown("#### 🛣️ LGED")
        if not lged_active.empty:
            st.write(f"**Active Version:** {lged_active.iloc[0]['version_name']} ({lged_active.iloc[0]['edition_year']})")
            
            if st.button("📸 Create LGED Rollback Point", use_container_width=True):
                st.info("Use the 'Create Snapshot' tab to create a snapshot")
        else:
            st.info("No active LGED version")
    
    st.markdown("---")
    st.warning("""
    ⚠️ **Rollback Warning:**
    - Rolling back to a snapshot will replace current data with the snapshot data
    - A backup snapshot is automatically created before rollback
    - This action cannot be undone (except by rolling back to the auto-backup)
    """)


def render_create_snapshot_tab(rollback_manager, db):
    """Create new rollback snapshot"""
    
    st.markdown("#### 💾 Create New Rollback Snapshot")
    
    col1, col2 = st.columns(2)
    
    with col1:
        source = st.radio(
            "Select Source",
            options=["PWD", "LGED"],
            horizontal=True
        )
    
    with col2:
        # Get versions for selected source
        conn = db.get_connection()
        versions_df = pd.read_sql_query("""
            SELECT id, version_name, edition_year, is_active 
            FROM rate_versions 
            WHERE source = ? 
            ORDER BY edition_year DESC
        """, conn, params=(source,))
        conn.close()
        
        if versions_df.empty:
            st.error(f"No {source} versions found. Please import a schedule first.")
            return
        
        selected_version = st.selectbox(
            "Select Version",
            options=versions_df['id'].tolist(),
            format_func=lambda x: f"{versions_df[versions_df['id']==x]['version_name'].iloc[0]} ({versions_df[versions_df['id']==x]['edition_year'].iloc[0]})"
        )
    
    snapshot_name = st.text_input(
        "Snapshot Name",
        value=f"{source} Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    description = st.text_area("Description (optional)", placeholder="What does this snapshot represent?")
    
    if st.button("📸 Create Snapshot", type="primary"):
        if snapshot_name:
            with st.spinner("Creating snapshot..."):
                snapshot_id = rollback_manager.create_snapshot(
                    source=source,
                    version_id=selected_version,
                    snapshot_name=snapshot_name,
                    created_by=st.session_state.get('username', 'admin'),
                    description=description
                )
                st.success(f"✅ Snapshot '{snapshot_name}' created successfully!")
                st.balloons()
                
                st.info(f"Snapshot ID: {snapshot_id}\nCreated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.error("Please enter a snapshot name")