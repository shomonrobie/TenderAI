# modules/manual_rate_entry.py

import streamlit as st
import pandas as pd
from datetime import datetime
import re
from modules.rbac import (
    rbac, can_edit_rates, can_delete_rates, can_import_rates,
    render_role_badge, require_permission, is_admin, is_company_admin
)

class ManualRateEntry:
    """Manual data entry interface for PWD and LGED rates with parent-child management"""
    
    def __init__(self, db):
        self.db = db
    
    def render(self):
        """Main manual entry interface with RBAC"""
        
        # Check permission
        if not can_edit_rates() and not can_import_rates():
            st.error("❌ You don't have permission to manually edit rates.")
            st.info("Contact your administrator to upgrade your permissions.")
            return
        
        # Render role badge
        render_role_badge()
        
        st.markdown("""
        <div class="main-header">
            <h1>📝 Manual Rate Entry</h1>
            <p>Copy-paste rates directly from PDF or Excel into the table below</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show permission info
        user_role = st.session_state.get('user_role', 'viewer')
        if user_role == 'analyst':
            st.info("📈 **Analyst Mode:** You can view and suggest edits, but cannot save to database.")
        elif user_role in ['manager', 'company_admin']:
            st.info("📊 **Manager Mode:** You can edit and save rate data.")
        elif is_admin():
            st.info("👑 **Admin Mode:** Full access to all rate management features.")
        
        # Source selection
        source = st.radio(
            "Select Rate Schedule",
            options=["PWD", "LGED"],
            horizontal=True,
            key="manual_entry_source"
        )
        
        # Edition year
        edition_year = st.number_input(
            "Edition Year",
            min_value=2020,
            max_value=2030,
            value=2022 if source == "PWD" else 2025,
            key="manual_edition_year"
        )
        
        st.markdown("---")
    
        # Create tabs for different operations
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "➕ Add New Items",
            "✏️ Edit Existing Items",
            "📋 Import from Text",
            "🌳 Parent-Child Builder",
            "📁 Upload CSV"
        ])

        with tab1:
            self._render_row_entry_interface(source, edition_year)
        
        with tab2:
            # Only show edit interface if user has edit permission
            if can_edit_rates():
                self.render_edit_interface(source, edition_year)
            else:
                st.info("🔒 You don't have permission to edit existing items. Contact your administrator.")
        
        with tab3:
            if can_import_rates() or can_edit_rates():
                self._render_paste_interface(source, edition_year)
            else:
                st.info("🔒 You don't have permission to import data.")
        
        with tab4:
            if can_edit_rates():
                self._render_parent_child_builder(source, edition_year)
            else:
                st.info("🔒 You don't have permission to manage parent-child relationships.")
        
        with tab5:
            if can_import_rates() or can_edit_rates():
                self._render_csv_upload_interface(source, edition_year)
            else:
                st.info("🔒 You don't have permission to upload CSV files.")
    
    def _render_parent_child_builder(self, source, edition_year):
        """Simplified parent-child relationship builder with RBAC"""
        
        st.markdown("### 🌳 Parent-Child Relationship Builder")
        st.caption("Build hierarchical structure by defining parents and their children")
        
        # Check if user can edit (for save operations)
        can_save = can_edit_rates()
        
        if not can_save:
            st.info("🔒 You have view-only access. Contact your administrator to edit parent-child relationships.")
        
        # Initialize session state
        if 'parent_child_data' not in st.session_state:
            st.session_state.parent_child_data = {
                'parents': [],
                'children': []
            }
        
        # Get chapters for this source
        if source == "PWD":
            chapters_df = self.db.get_pwd_chapters()
        else:
            chapters_df = self.db.get_lged_chapters()
        
        # Create chapter options
        chapter_options = ["-- Select Chapter --"]
        chapter_map = {}
        for _, row in chapters_df.iterrows():
            display_text = f"{row['chapter_number']} - {row['chapter_name']}"
            chapter_options.append(display_text)
            chapter_map[display_text] = row['chapter_number']
        
        # ========== ADD PARENT SECTION ==========
        st.markdown("#### 📁 Add Parent Item")
        st.caption("Parent items have NO rates - they are just descriptive headers")
        
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                parent_code = st.text_input("Parent Code", placeholder="1.01 or 01.1", key="parent_code_simple", disabled=not can_save)
                selected_chapter_display = st.selectbox("Chapter", chapter_options, key="parent_chapter_simple", disabled=not can_save)
                if selected_chapter_display != "-- Select Chapter --":
                    parent_chapter = chapter_map[selected_chapter_display]
                else:
                    parent_chapter = ""
            
            with col2:
                parent_desc = st.text_area("Parent Description", placeholder="Full description of the parent item", height=100, key="parent_desc_simple", disabled=not can_save)
            
            if can_save:
                if st.button("➕ Add Parent", key="add_parent_simple"):
                    if parent_code and parent_desc and parent_chapter:
                        existing = [p for p in st.session_state.parent_child_data['parents'] if p['code'] == parent_code]
                        if not existing:
                            st.session_state.parent_child_data['parents'].append({
                                'code': parent_code,
                                'description': parent_desc,
                                'chapter': parent_chapter,
                                'children_count': 0
                            })
                            st.success(f"✅ Added parent: {parent_code}")
                            st.rerun()
                        else:
                            st.warning("Parent code already exists!")
                    else:
                        st.error("Please fill all fields")
        
        st.markdown("---")
        
        # ========== ADD CHILD SECTION ==========
        st.markdown("#### 👶 Add Child Item")
        st.caption("Child items HAVE rates and belong to a parent")
        
        parent_options = [p['code'] for p in st.session_state.parent_child_data['parents']]
        
        if not parent_options:
            st.info("💡 No parents available. Please add a parent first.")
        else:
            with st.container():
                col1, col2 = st.columns(2)
                
                with col1:
                    child_code = st.text_input("Child Code", placeholder="1.01.01 or 01.1.1", key="child_code_simple", disabled=not can_save)
                    selected_parent = st.selectbox("Select Parent", parent_options, key="child_parent_simple", disabled=not can_save)
                    unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key="child_unit_simple", disabled=not can_save)
                
                with col2:
                    child_desc = st.text_area("Child Description", placeholder="Description of the child item", height=100, key="child_desc_simple", disabled=not can_save)
                    
                    if source == "PWD":
                        zone_labels = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
                    else:
                        zone_labels = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
                    
                    st.markdown("##### Rates")
                    rate_cols = st.columns(4)
                    rates = {}
                    for i, label in enumerate(zone_labels):
                        with rate_cols[i]:
                            rates[label] = st.number_input(label, value=0.0, step=100.0, format="%.2f", key=f"child_rate_{label}", disabled=not can_save)
                
                if can_save:
                    if st.button("➕ Add Child", key="add_child_simple"):
                        if child_code and child_desc and selected_parent:
                            if not child_code.startswith(selected_parent):
                                st.warning(f"⚠️ Child code should start with parent code '{selected_parent}'")
                            else:
                                existing = [c for c in st.session_state.parent_child_data['children'] if c['code'] == child_code]
                                if not existing:
                                    st.session_state.parent_child_data['children'].append({
                                        'code': child_code,
                                        'parent_code': selected_parent,
                                        'description': child_desc,
                                        'unit': unit,
                                        'rates': rates
                                    })
                                    for p in st.session_state.parent_child_data['parents']:
                                        if p['code'] == selected_parent:
                                            p['children_count'] += 1
                                            break
                                    st.success(f"✅ Added child: {child_code} under parent {selected_parent}")
                                    st.rerun()
                                else:
                                    st.warning("Child code already exists!")
                        else:
                            st.error("Please fill all fields")
        
        st.markdown("---")
        
        # ========== DISPLAY CURRENT DATA ==========
        if st.session_state.parent_child_data['parents'] or st.session_state.parent_child_data['children']:
            st.markdown("#### 📋 Current Data")
            
            if st.session_state.parent_child_data['parents']:
                st.markdown("**Parents:**")
                parents_df = pd.DataFrame([{
                    'Code': p['code'],
                    'Chapter': p.get('chapter', ''),
                    'Description': p['description'][:80] + ('...' if len(p['description']) > 80 else ''),
                    'Children': p['children_count']
                } for p in st.session_state.parent_child_data['parents']])
                st.dataframe(parents_df, use_container_width=True, hide_index=True)
            
            if st.session_state.parent_child_data['children']:
                st.markdown("**Children:**")
                children_data = []
                for child in st.session_state.parent_child_data['children']:
                    row = {
                        'Code': child['code'],
                        'Parent': child['parent_code'],
                        'Description': child['description'][:60] + ('...' if len(child['description']) > 60 else ''),
                        'Unit': child['unit']
                    }
                    for zone, rate in child['rates'].items():
                        if rate > 0:
                            row[zone] = f"৳{rate:,.2f}"
                    children_data.append(row)
                
                children_df = pd.DataFrame(children_data)
                st.dataframe(children_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # ========== ACTION BUTTONS ==========
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Export to CSV", use_container_width=True):
                parents_df = pd.DataFrame(st.session_state.parent_child_data['parents'])
                children_df = pd.DataFrame(st.session_state.parent_child_data['children'])
                
                import io
                import zipfile
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.writestr(f'parents_{source}.csv', parents_df.to_csv(index=False))
                    zip_file.writestr(f'children_{source}.csv', children_df.to_csv(index=False))
                
                st.download_button(
                    "Download ZIP",
                    zip_buffer.getvalue(),
                    f"parent_child_{source}.zip",
                    "application/zip",
                    key="download_zip"
                )
        
        with col2:
            if can_save:
                if st.button("💾 Save to Database", type="primary", use_container_width=True):
                    if st.session_state.parent_child_data['parents'] or st.session_state.parent_child_data['children']:
                        self._save_hierarchy_to_db(st.session_state.parent_child_data, source, edition_year)
                    else:
                        st.warning("No data to save")
            else:
                st.button("🔒 Save to Database", disabled=True, use_container_width=True, help="You don't have permission to save")
        
        with col3:
            if can_save and st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.parent_child_data = {'parents': [], 'children': []}
                st.rerun()
    def _save_hierarchy_to_db(self, data, source, edition_year):
        """Save parent-child hierarchy to database with RBAC check"""
        
        # Double-check permission before saving
        if not can_edit_rates():
            st.error("❌ You don't have permission to save rate data.")
            return
        
        try:
            if source == "PWD":
                self.db.init_pwd_hierarchical_tables()
            else:
                self.db.init_lged_tables()
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create version
            from datetime import date
            version_name = f"Manual Entry {source} {edition_year}"
            
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source, version_name, edition_year, date.today(), True, datetime.now(), 'manual_entry'))
            
            version_id = cursor.lastrowid
            
            # Save parents
            for parent in data['parents']:
                chapter = parent.get('chapter', parent['code'].split('.')[0])
                
                if source == "PWD":
                    cursor.execute("""
                        INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                        VALUES (?, ?, ?, ?)
                    """, (parent['code'], parent['description'], chapter, version_id))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO lged_parents (code, description, chapter_number, version_id)
                        VALUES (?, ?, ?, ?)
                    """, (parent['code'], parent['description'], chapter, version_id))
            
            # Save children
            for child in data['children']:
                if source == "PWD":
                    cursor.execute("""
                        INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (child['code'], child['parent_code'], child['description'], child['unit'], edition_year, version_id))
                    
                    for zone, rate in child['rates'].items():
                        if rate > 0:
                            cursor.execute("""
                                INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                                VALUES (?, ?, ?, ?, ?)
                            """, (child['code'], zone, rate, edition_year, version_id))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO lged_children (code, parent_code, description, unit, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (child['code'], child['parent_code'], child['description'], child['unit'], edition_year, version_id))
                    
                    child_id = cursor.lastrowid
                    
                    for zone, rate in child['rates'].items():
                        if rate > 0:
                            cursor.execute("""
                                INSERT INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                                VALUES (?, ?, ?, ?)
                            """, (child_id, zone, rate, version_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {len(data['parents'])} parents and {len(data['children'])} children to {source} database!")
            st.balloons()
            
            # Option to clear after save
            if st.button("Clear Form After Save", key="clear_form_after_save"):
                st.session_state.parent_child_data = {'parents': [], 'children': []}
                st.rerun()
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    def render_chapter_management(self, source):
        """Render chapter management interface"""
        
        st.markdown("### 📚 Chapter Management")
        
        self.db.init_chapters_tables()
        
        if source == "PWD":
            chapters_df = self.db.get_pwd_chapters()
        else:
            chapters_df = self.db.get_lged_chapters()
        
        # Display existing chapters
        st.markdown("#### Existing Chapters")
        st.dataframe(chapters_df, use_container_width=True, hide_index=True)
        
        # Add new chapter
        with st.expander("➕ Add New Chapter", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                new_chapter_num = st.text_input("Chapter Number", placeholder="01 or 1")
            with col2:
                new_chapter_name = st.text_input("Chapter Name", placeholder="Chapter name")
            
            new_chapter_desc = st.text_area("Description (optional)", height=80)
            
            if st.button("Add Chapter", key="add_chapter_btn"):
                if new_chapter_num and new_chapter_name:
                    if source == "PWD":
                        self.db.add_pwd_chapter(new_chapter_num, new_chapter_name, new_chapter_desc)
                    else:
                        self.db.add_lged_chapter(new_chapter_num, new_chapter_name, new_chapter_desc)
                    st.success(f"Added chapter {new_chapter_num}: {new_chapter_name}")
                    st.rerun()
    
    

    def _render_paste_interface(self, source, edition_year):
        """Interface for pasting tabular data"""
        
        st.markdown("### 📋 Paste Data")
        st.caption("Copy rows from Excel/PDF and paste below. Format: Code\tDescription\tUnit\tZone1\tZone2\tZone3\tZone4")
        
        # Example format
        if source == "PWD":
            st.info("**Example format (tab-separated):**\n```\n01.1.1\tEngineer's site office 10 sqm\tjob\t50308.10\t50308.00\t50308.00\t50308.00\n01.1.2\tEngineer's site office 15 sqm\tjob\t80370.26\t80370.00\t80370.00\t80370.00```")
        else:
            st.info("**Example format (tab-separated):**\n```\n1.01.01\tEngineer's site office 10 sqm\tjob\t51705.44\t51705.44\t51705.44\t51705.44\n1.01.02\tEngineer's site office 15 sqm\tjob\t82602.50\t82602.50\t82602.50\t82602.50```")
        
        # Text area for pasting
        pasted_text = st.text_area(
            "Paste your data here",
            height=200,
            placeholder="Code\tDescription\tUnit\tZone1\tZone2\tZone3\tZone4\n01.1.1\tEngineer's site office\tjob\t50308.10\t50308.00\t50308.00\t50308.00"
        )
        
        # Option to specify if data includes headers
        has_header = st.checkbox("First row is header", value=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Preview Data", use_container_width=True, key="preview_data"):
                if pasted_text:
                    df = self._parse_pasted_data(pasted_text, source, has_header)
                    if df is not None:
                        st.session_state.preview_df = df
                        st.success(f"✅ Parsed {len(df)} rows")
                    else:
                        st.error("Failed to parse data. Check format.")
        
        with col2:
            if st.button("💾 Save to Database", type="primary", use_container_width=True, key="save_to_database"):
                if hasattr(st.session_state, 'preview_df'):
                    self._save_to_database(st.session_state.preview_df, source, edition_year)
                else:
                    st.warning("Please preview data first")
        
        # Show preview
        if hasattr(st.session_state, 'preview_df'):
            st.markdown("#### Preview")
            st.dataframe(st.session_state.preview_df, use_container_width=True, hide_index=True)
    
    def _save_child_items_only(self, rows, source, edition_year):
        """Save only child items (no parent creation)"""
        
        try:
            # ✅ REMOVED: self.db.init_pwd_hierarchical_tables() and self.db.init_lged_tables()
            # Tables already exist in unified manager
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create version
            from datetime import date
            version_name = f"Manual Entry {source} {edition_year}"
            
            
            # Table already exists in unified manager
            
            # Insert version
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (source, version_name, edition_year, date.today(), datetime.now(), 'manual_entry'))
            
            version_id = cursor.lastrowid
            
            # Save children only (parents should already exist)
            children_saved = 0
            rates_saved = 0
            
            for row in rows:
                code = row['code']
                parent_code = row['parent_code']
                description = row['description']
                unit = row.get('unit', '')
                
                # Verify parent exists
                if source == "PWD":
                    cursor.execute("SELECT 1 FROM pwd_parents WHERE pwd_code = ?", (parent_code,))
                else:
                    cursor.execute("SELECT 1 FROM lged_parents WHERE code = ?", (parent_code,))
                
                if not cursor.fetchone():
                    st.warning(f"Parent '{parent_code}' not found. Skipping child '{code}'")
                    continue
                
                # Add child
                if source == "PWD":
                    cursor.execute("""
                        INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (code, parent_code, description, unit, edition_year, version_id))
                    children_saved += 1
                    
                    for zone in ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']:
                        rate = row.get(zone, 0)
                        if rate > 0:
                            cursor.execute("""
                                INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                                VALUES (?, ?, ?, ?, ?)
                            """, (code, zone, float(rate), edition_year, version_id))
                            rates_saved += 1
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO lged_children (code, parent_code, description, unit, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (code, parent_code, description, unit, edition_year, version_id))
                    child_id = cursor.lastrowid
                    children_saved += 1
                    
                    for zone in ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']:
                        rate = row.get(zone, 0)
                        if rate > 0:
                            cursor.execute("""
                                INSERT INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                                VALUES (?, ?, ?, ?)
                            """, (child_id, zone, float(rate), version_id))
                            rates_saved += 1
            
            # Update version statistics
            cursor.execute("""
                UPDATE rate_versions 
                SET total_children = ?, total_rates = ?
                WHERE id = ?
            """, (children_saved, rates_saved, version_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {children_saved} children and {rates_saved} rates to {source} database!")
            st.balloons()
            
            # Clear rows
            st.session_state.manual_rows = []
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    def _render_row_entry_interface(self, source, edition_year):
        """Simplified row-by-row entry - for CHILD items only (with rates)"""
        
        st.markdown("### ✏️ Add Child Items")
        st.caption("Add child items with rates. Parent items should be created in 'Parent-Child Builder' first.")
        
        # Initialize session state for rows
        if 'manual_rows' not in st.session_state:
            st.session_state.manual_rows = []
        
        # Load existing parents from database
        existing_parents = self._get_existing_parents(source)
        
        if not existing_parents:
            st.warning("⚠️ No parents found in database. Please add parents using the 'Parent-Child Builder' tab first.")
            return
        
        # Input form for child items only
        with st.form("add_child_form", clear_on_submit=True):
            st.markdown("#### New Child Item")
            
            col1, col2 = st.columns(2)
            
            with col1:
                code = st.text_input("Item Code", placeholder="1.01.01 or 01.1.1", help="Child code must start with parent code")
                
                # Parent selection (required)
                parent_options = ["-- Select Parent --"] + [f"{p['code']} - {p['description'][:50]}..." for p in existing_parents]
                selected_parent_display = st.selectbox("Select Parent", parent_options, key="child_parent_select")
                
                if selected_parent_display != "-- Select Parent --":
                    parent_code = selected_parent_display.split(" - ")[0]
                    st.info(f"📁 Parent: {parent_code}")
                    
                    # Validate child code format
                    if code and not code.startswith(parent_code):
                        st.warning(f"⚠️ Child code should start with '{parent_code}'")
                else:
                    parent_code = ""
                
                unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key="child_unit")
            
            with col2:
                description = st.text_area("Description", placeholder="Item description", height=100, key="child_desc")
            
            # Rate fields (always shown for child items)
            if source == "PWD":
                zone_labels = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
            else:
                zone_labels = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
            
            st.markdown("##### Rates")
            rate_cols = st.columns(4)
            rates = {}
            for i, label in enumerate(zone_labels):
                with rate_cols[i]:
                    rates[label] = st.number_input(label, value=0.0, step=100.0, format="%.2f", key=f"child_rate_{label}")
            
            submitted = st.form_submit_button("➕ Add Child Item", use_container_width=True)
            
            if submitted and code and description and parent_code:
                # Validate child code format
                if not code.startswith(parent_code):
                    st.error(f"Child code must start with parent code '{parent_code}'")
                else:
                    new_row = {
                        'code': code,
                        'parent_code': parent_code,
                        'description': description,
                        'unit': unit,
                        zone_labels[0]: rates[zone_labels[0]],
                        zone_labels[1]: rates[zone_labels[1]],
                        zone_labels[2]: rates[zone_labels[2]],
                        zone_labels[3]: rates[zone_labels[3]]
                    }
                    st.session_state.manual_rows.append(new_row)
                    st.success(f"✅ Added child: {code} → Parent: {parent_code}")
                    st.rerun()
            elif submitted:
                st.error("Please fill all required fields (Code, Description, and Parent)")
        
        # Display current rows
        if st.session_state.manual_rows:
            st.markdown("#### Current Child Items")
            
            display_rows = []
            for row in st.session_state.manual_rows:
                display_rows.append({
                    'Code': row['code'],
                    'Parent': row['parent_code'],
                    'Description': row['description'][:60] + ('...' if len(row['description']) > 60 else ''),
                    'Unit': row['unit']
                })
            
            df_display = pd.DataFrame(display_rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.manual_rows = []
                    st.rerun()
            
            with col2:
                if st.button("📥 Export to CSV", use_container_width=True):
                    export_df = pd.DataFrame(st.session_state.manual_rows)
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        "Download CSV",
                        csv,
                        f"child_items_{source}_{edition_year}.csv",
                        "text/csv"
                    )
            
            with col3:
                if st.button("💾 Save to Database", type="primary", use_container_width=True):
                    self._save_child_items_only(st.session_state.manual_rows, source, edition_year)

    def _render_row_entry_interface_bak(self, source, edition_year):
        """Row-by-row entry interface with parent selection"""
        
        st.markdown("### ✏️ Row by Row Entry")
        st.caption("Add items one at a time. Select parent from existing parents or create new parent.")
        
        # Initialize session state for rows
        if 'manual_rows' not in st.session_state:
            st.session_state.manual_rows = []
        
        # Load existing parents from database for this source
        existing_parents = self._get_existing_parents(source)
        
        # Input form
        with st.form("add_row_form", clear_on_submit=True):
            st.markdown("#### New Item")
            
            col1, col2 = st.columns(2)
            
            with col1:
                code = st.text_input("Item Code", placeholder="01.1.1 or 1.01.01", help="Use dot notation (e.g., 01.1.1)")
                
                # Parent selection options
                parent_option = st.radio(
                    "Parent Option",
                    options=["Select from existing parent", "Create new parent", "Self (item is its own parent)"],
                    horizontal=True,
                    key="parent_option"
                )
                
                if parent_option == "Select from existing parent":
                    parent_options = ["-- Select Parent --"] + [f"{p['code']} - {p['description'][:50]}..." for p in existing_parents]
                    selected_parent_display = st.selectbox("Select Parent", parent_options, key="selected_parent")
                    
                    if selected_parent_display != "-- Select Parent --":
                        parent_code = selected_parent_display.split(" - ")[0]
                        st.info(f"✅ Selected parent: {parent_code}")
                    else:
                        parent_code = ""
                
                elif parent_option == "Create new parent":
                    parent_code = st.text_input("New Parent Code", placeholder="01.1 or 1.01", key="new_parent_code_2")
                    parent_description = st.text_area("Parent Description", placeholder="Description for the new parent", height=80, key="new_parent_desc")
                    if parent_code and parent_description:
                        st.info(f"📁 Will create new parent: {parent_code}")
                
                else:  # Self parent
                    # Extract parent from code (e.g., 01.1.1 -> parent is 01.1)
                    if code and '.' in code:
                        code_parts = code.split('.')
                        if len(code_parts) >= 2:
                            parent_code = '.'.join(code_parts[:2])
                            st.info(f"🔄 Self-parent: This item's parent will be **{parent_code}** (same as item code prefix)")
                        else:
                            parent_code = code
                            st.info(f"🔄 Self-parent: Parent will be **{parent_code}**")
                    else:
                        parent_code = ""
                        st.warning("Enter item code first to auto-detect parent")
            
            with col2:
                description = st.text_area("Description", placeholder="Item description", height=100, key="row_desc")
                unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key="row_unit")
            
            # Rate fields
            if source == "PWD":
                zone_labels = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
            else:
                zone_labels = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
            
            st.markdown("##### Rates")
            rate_cols = st.columns(4)
            rates = {}
            for i, label in enumerate(zone_labels):
                with rate_cols[i]:
                    rates[label] = st.number_input(label, value=0.0, step=100.0, format="%.2f", key=f"row_rate_{label}")
            
            submitted = st.form_submit_button("➕ Add Row", use_container_width=True)
            
            if submitted and code and description:
                # Validate parent
                if parent_option == "Select from existing parent" and not parent_code:
                    st.error("Please select a parent")
                    return
                elif parent_option == "Create new parent" and (not parent_code or not parent_description):
                    st.error("Please enter both parent code and description")
                    return
                elif parent_option == "Self" and not parent_code:
                    st.error("Please enter item code first")
                    return
                
                new_row = {
                    'code': code,
                    'parent_code': parent_code,
                    'parent_option': parent_option,
                    'description': description,
                    'unit': unit,
                    'new_parent_desc': parent_description if parent_option == "Create new parent" else "",
                    zone_labels[0]: rates[zone_labels[0]],
                    zone_labels[1]: rates[zone_labels[1]],
                    zone_labels[2]: rates[zone_labels[2]],
                    zone_labels[3]: rates[zone_labels[3]]
                }
                st.session_state.manual_rows.append(new_row)
                st.success(f"✅ Added: {code} → Parent: {parent_code}")
                st.rerun()
        
        # Display current rows with parent info
        if st.session_state.manual_rows:
            st.markdown("#### Current Rows")
            
            # Prepare display data
            display_rows = []
            for row in st.session_state.manual_rows:
                display_rows.append({
                    'Code': row['code'],
                    'Parent': row['parent_code'],
                    'Parent Type': row['parent_option'],
                    'Description': row['description'][:60],
                    'Unit': row['unit']
                })
            
            df_display = pd.DataFrame(display_rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Show detailed view with rates
            with st.expander("🔍 Show Full Details with Rates", expanded=False):
                full_df = pd.DataFrame(st.session_state.manual_rows)
                st.dataframe(full_df, use_container_width=True, hide_index=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Clear All Rows", use_container_width=True,key="clear_all_rows"):
                    st.session_state.manual_rows = []
                    st.rerun()
            
            with col2:
                if st.button("📥 Export to CSV", use_container_width=True, key="export_to_csv_2"):
                    export_df = pd.DataFrame(st.session_state.manual_rows)
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        "Download CSV",
                        csv,
                        f"manual_rates_{source}_{edition_year}.csv",
                        "text/csv",
                        key="export_rows_csv"
                    )
            
            with col3:
                if st.button("💾 Save to Database", type="primary", use_container_width=True, key="save_to_database_4"):
                    self._save_row_data_with_parents(st.session_state.manual_rows, source, edition_year)


    def _get_existing_parents(self, source):
        """Get existing parents from database for parent selection"""
        try:
            conn = self.db.get_connection()
            if source == "PWD":
                # Check if table exists and has data
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pwd_parents'")
                if not cursor.fetchone():
                    return []
                
                df = pd.read_sql_query("""
                    SELECT pwd_code as code, description 
                    FROM pwd_parents 
                    ORDER BY pwd_code
                """, conn)
            else:
                # Check if table exists and has data
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lged_parents'")
                if not cursor.fetchone():
                    return []
                
                df = pd.read_sql_query("""
                    SELECT code, description 
                    FROM lged_parents 
                    ORDER BY code
                """, conn)
            
            conn.close()
            
            if df.empty:
                return []
            
            return df.to_dict('records')
        except Exception as e:
            st.warning(f"Could not load existing parents: {e}")
            return []


    def _save_row_data_with_parents(self, rows, source, edition_year):
        """Save row-by-row entered data with parent creation"""
        
        try:
            # ✅ REMOVED: self.db.init_pwd_hierarchical_tables(), init_lged_tables(), init_chapters_tables()
            # Tables already exist in unified manager
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create version
            from datetime import date
            version_name = f"Manual Entry {source} {edition_year}"
            
            
            # Table already exists in unified manager
            
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source, version_name, edition_year, date.today(), True, datetime.now(), 'manual_entry'))
            
            version_id = cursor.lastrowid
            
            # Track created parents to avoid duplicates
            created_parents = set()
            
            # First, create all new parents
            for row in rows:
                if row['parent_option'] == "Create new parent":
                    parent_code = row['parent_code']
                    parent_desc = row.get('new_parent_desc', f"Parent of {parent_code}")
                    chapter = row.get('chapter', parent_code.split('.')[0] if '.' in parent_code else "01")
                    
                    if parent_code not in created_parents:
                        if source == "PWD":
                            # Check if parent already exists
                            cursor.execute("SELECT 1 FROM pwd_parents WHERE pwd_code = ?", (parent_code,))
                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                                    VALUES (?, ?, ?, ?)
                                """, (parent_code, parent_desc, chapter, version_id))
                                created_parents.add(parent_code)
                                st.info(f"📁 Created parent: {parent_code}")
                        else:
                            cursor.execute("SELECT 1 FROM lged_parents WHERE code = ?", (parent_code,))
                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO lged_parents (code, description, chapter_number, version_id)
                                    VALUES (?, ?, ?, ?)
                                """, (parent_code, parent_desc, chapter, version_id))
                                created_parents.add(parent_code)
                                st.info(f"📁 Created parent: {parent_code}")
            
            # Then save all children
            children_saved = 0
            rates_saved = 0
            
            for row in rows:
                code = row['code']
                parent_code = row['parent_code']
                description = row['description']
                unit = row.get('unit', '')
                chapter = row.get('chapter', code.split('.')[0] if '.' in code else "01")
                
                # Ensure parent exists (for self-parent case or if parent wasn't created)
                if source == "PWD":
                    cursor.execute("SELECT 1 FROM pwd_parents WHERE pwd_code = ?", (parent_code,))
                    if not cursor.fetchone():
                        # Create parent if it doesn't exist
                        parent_desc = f"Parent of {parent_code}"
                        cursor.execute("""
                            INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                            VALUES (?, ?, ?, ?)
                        """, (parent_code, parent_desc, chapter, version_id))
                        st.info(f"📁 Auto-created parent: {parent_code}")
                else:
                    cursor.execute("SELECT 1 FROM lged_parents WHERE code = ?", (parent_code,))
                    if not cursor.fetchone():
                        parent_desc = f"Parent of {parent_code}"
                        cursor.execute("""
                            INSERT INTO lged_parents (code, description, chapter_number, version_id)
                            VALUES (?, ?, ?, ?)
                        """, (parent_code, parent_desc, chapter, version_id))
                        st.info(f"📁 Auto-created parent: {parent_code}")
                
                # Add child item
                if source == "PWD":
                    # Check if child already exists
                    cursor.execute("SELECT 1 FROM pwd_children WHERE pwd_code = ?", (code,))
                    if cursor.fetchone():
                        # Update existing
                        cursor.execute("""
                            UPDATE pwd_children 
                            SET parent_code = ?, description = ?, unit = ?, edition_year = ?, version_id = ?
                            WHERE pwd_code = ?
                        """, (parent_code, description, unit, edition_year, version_id, code))
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (code, parent_code, description, unit, edition_year, version_id))
                    
                    children_saved += 1
                    
                    # Save rates
                    for zone in ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']:
                        rate = row.get(zone, 0)
                        if rate and rate > 0:
                            cursor.execute("""
                                INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                                VALUES (?, ?, ?, ?, ?)
                            """, (code, zone, float(rate), edition_year, version_id))
                            rates_saved += 1
                else:
                    # LGED
                    cursor.execute("SELECT 1 FROM lged_children WHERE code = ?", (code,))
                    if cursor.fetchone():
                        # Update existing
                        cursor.execute("""
                            UPDATE lged_children 
                            SET parent_code = ?, description = ?, unit = ?, edition_year = ?, version_id = ?
                            WHERE code = ?
                        """, (parent_code, description, unit, edition_year, version_id, code))
                        cursor.execute("SELECT id FROM lged_children WHERE code = ?", (code,))
                        child_id = cursor.fetchone()[0]
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO lged_children (code, parent_code, description, unit, edition_year, version_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (code, parent_code, description, unit, edition_year, version_id))
                        child_id = cursor.lastrowid
                    
                    children_saved += 1
                    
                    # Save rates
                    for zone in ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']:
                        rate = row.get(zone, 0)
                        if rate and rate > 0:
                            cursor.execute("""
                                INSERT OR REPLACE INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                                VALUES (?, ?, ?, ?)
                            """, (child_id, zone, float(rate), version_id))
                            rates_saved += 1
            
            # Update version statistics
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?
                WHERE id = ?
            """, (len(created_parents), children_saved, rates_saved, version_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {len(created_parents)} parents, {children_saved} children, and {rates_saved} rates to {source} database!")
            st.balloons()
            
            # Clear rows
            st.session_state.manual_rows = []
            
            # Refresh parent list for next entries
            st.rerun()
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    def _debug_show_parents(self, source):
        """Debug function to show what parents exist in database"""
        try:
            conn = self.db.get_connection()
            if source == "PWD":
                df = pd.read_sql_query("SELECT pwd_code, description FROM pwd_parents LIMIT 10", conn)
            else:
                df = pd.read_sql_query("SELECT code, description FROM lged_parents LIMIT 10", conn)
            conn.close()
            
            if not df.empty:
                st.write(f"Parents in database ({len(df)}):")
                st.dataframe(df)
            else:
                st.write("No parents found in database")
        except Exception as e:
            st.write(f"Error checking parents: {e}")
    
    def _render_row_entry_interface(self, source, edition_year):
        """Row-by-row entry interface with parent selection and chapter"""
        
        st.markdown("### ✏️ Row by Row Entry")
        st.caption("Add items one at a time. Select parent from existing parents or create new parent.")
        
        # Initialize chapters table if needed
        self.db.init_chapters_tables()
        
        # Initialize session state for rows
        if 'manual_rows' not in st.session_state:
            st.session_state.manual_rows = []
        
        # Load existing parents and chapters
        existing_parents = self._get_existing_parents(source)
        # ========== ADD DEBUG HERE ==========
        # Show debug info to check what parents exist
        if st.checkbox("🔍 Show debug info", key="debug_parents"):
            st.markdown("#### Debug: Available Parents")
            if existing_parents:
                st.write(f"Found {len(existing_parents)} parents:")
                debug_df = pd.DataFrame(existing_parents)
                st.dataframe(debug_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No parents found in database!")
            
            # Also show what's in the database directly
            self._debug_show_parents(source)

        # Get chapters for this source with display formatting
        if source == "PWD":
            chapters_df = self.db.get_pwd_chapters()
        else:
            chapters_df = self.db.get_lged_chapters()
        
        # Create display options with chapter number and name
        chapter_options = ["-- Select Chapter --"]
        chapter_map = {}  # Maps display text to actual chapter number
        
        for _, row in chapters_df.iterrows():
            display_text = f"{row['chapter_number']} - {row['chapter_name']}"
            chapter_options.append(display_text)
            chapter_map[display_text] = row['chapter_number']
        
        # Input form
        with st.form("add_row_form", clear_on_submit=True):
            st.markdown("#### New Item")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Chapter selection with display formatting
                selected_display = st.selectbox("Chapter", chapter_options, key="row_chapter")
                
                # Get actual chapter number from selection
                if selected_display != "-- Select Chapter --":
                    selected_chapter = chapter_map[selected_display]
                else:
                    selected_chapter = ""
                
                code = st.text_input("Item Code", placeholder="01.1.1 or 1.01.01", help="Use dot notation (e.g., 01.1.1)")
                
                # Auto-fill chapter prefix if code is entered
                if code and (not selected_chapter or selected_chapter == "-- Select Chapter --"):
                    code_parts = code.split('.')
                    if code_parts and code_parts[0].isdigit():
                        suggested_chapter = code_parts[0]
                        # Find matching chapter display
                        for display, chap_num in chapter_map.items():
                            if chap_num == suggested_chapter:
                                st.info(f"💡 Suggested chapter: {display}")
                                break
                
                # Parent selection options
                parent_option = st.radio(
                    "Parent Option",
                    options=["Select from existing parent", "Create new parent", "Self (item is its own parent)"],
                    horizontal=True,
                    key="parent_option"
                )
                
                if parent_option == "Select from existing parent":
                    parent_options = ["-- Select Parent --"] + [f"{p['code']} - {p['description'][:50]}..." for p in existing_parents]
                    selected_parent_display = st.selectbox("Select Parent", parent_options, key="selected_parent")
                    
                    if selected_parent_display != "-- Select Parent --":
                        parent_code = selected_parent_display.split(" - ")[0]
                        st.info(f"✅ Selected parent: {parent_code}")
                    else:
                        parent_code = ""
                
                elif parent_option == "Create new parent":
                    parent_code = st.text_input("New Parent Code", placeholder="01.1 or 1.01", key="new_parent_code_3")
                    parent_description = st.text_area("Parent Description", placeholder="Description for the new parent", height=80, key="new_parent_desc")
                    if parent_code and parent_description:
                        st.info(f"📁 Will create new parent: {parent_code}")
                
                else:  # Self parent
                    if code and '.' in code:
                        code_parts = code.split('.')
                        if len(code_parts) >= 2:
                            parent_code = '.'.join(code_parts[:2])
                            st.info(f"🔄 Self-parent: This item's parent will be **{parent_code}**")
                        else:
                            parent_code = code
                    else:
                        parent_code = ""
            
            with col2:
                description = st.text_area("Description", placeholder="Item description", height=150, key="row_desc")
                unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key="row_unit")
            
            # Rate fields
            if source == "PWD":
                zone_labels = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
            else:
                zone_labels = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
            
            st.markdown("##### Rates")
            rate_cols = st.columns(4)
            rates = {}
            for i, label in enumerate(zone_labels):
                with rate_cols[i]:
                    rates[label] = st.number_input(label, value=0.0, step=100.0, format="%.2f", key=f"row_rate_{label}")
            
            submitted = st.form_submit_button("➕ Add Row", use_container_width=True)
            
            if submitted and code and description:
                # Validate chapter
                if not selected_chapter:
                    st.error("Please select a chapter")
                    return
                
                # Validate parent
                if parent_option == "Select from existing parent" and not parent_code:
                    st.error("Please select a parent")
                    return
                elif parent_option == "Create new parent" and (not parent_code or not parent_description):
                    st.error("Please enter both parent code and description")
                    return
                
                new_row = {
                    'code': code,
                    'chapter': selected_chapter,  # Store actual chapter number
                    'chapter_display': selected_display,  # Store display for reference
                    'parent_code': parent_code,
                    'parent_option': parent_option,
                    'description': description,
                    'unit': unit,
                    'new_parent_desc': parent_description if parent_option == "Create new parent" else "",
                    zone_labels[0]: rates[zone_labels[0]],
                    zone_labels[1]: rates[zone_labels[1]],
                    zone_labels[2]: rates[zone_labels[2]],
                    zone_labels[3]: rates[zone_labels[3]]
                }
                st.session_state.manual_rows.append(new_row)
                
                # Show success with chapter display
                chapter_show = selected_display if selected_display != "-- Select Chapter --" else selected_chapter
                st.success(f"✅ Added: {code} → Chapter: {chapter_show}, Parent: {parent_code}")
                st.rerun()
        
        # Display current rows
        if st.session_state.manual_rows:
            st.markdown("#### Current Rows")
            
            display_rows = []
            for row in st.session_state.manual_rows:
                # Use chapter_display if available, otherwise fallback to chapter number
                chapter_display_value = row.get('chapter_display', row.get('chapter', 'N/A'))
                display_rows.append({
                    'Chapter': chapter_display_value,
                    'Code': row['code'],
                    'Parent': row['parent_code'],
                    'Parent Type': row['parent_option'],
                    'Description': row['description'][:60] + ('...' if len(row['description']) > 60 else ''),
                    'Unit': row['unit']
                })
            
            df_display = pd.DataFrame(display_rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Add delete row functionality
            st.markdown("#### Remove Rows")
            rows_to_delete = st.multiselect(
                "Select rows to delete",
                options=[f"{i+1}. {r['code']} - {r['description'][:50]}" for i, r in enumerate(st.session_state.manual_rows)],
                key="rows_to_delete"
            )
            
            if rows_to_delete and st.button("🗑️ Delete Selected Rows", key="delete_selected_rows"):
                indices_to_delete = [int(r.split('.')[0]) - 1 for r in rows_to_delete]
                st.session_state.manual_rows = [r for i, r in enumerate(st.session_state.manual_rows) if i not in indices_to_delete]
                st.rerun()
            
            # Save and export buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Clear All Rows", use_container_width=True, key="clear_all_rows"):
                    st.session_state.manual_rows = []
                    st.rerun()
            
            with col2:
                if st.button("📥 Export to CSV", use_container_width=True, key="export_to_csv_2"):
                    export_df = pd.DataFrame(st.session_state.manual_rows)
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        "Download CSV",
                        csv,
                        f"manual_rates_{source}_{edition_year}.csv",
                        "text/csv",
                        key="export_rows_csv"
                    )
            
            with col3:
                if st.button("💾 Save to Database", type="primary", use_container_width=True, key="save_to_database_5"):
                    self._save_row_data_with_parents(st.session_state.manual_rows, source, edition_year)
    def _render_csv_upload_interface(self, source, edition_year):
        """CSV upload interface"""
        
        st.markdown("### 📁 Upload CSV File")
        st.caption("CSV should have columns: code, description, unit, and zone columns")
        
        # Show expected format
        if source == "PWD":
            expected_cols = "code, description, unit, Dhaka, Chattogram, Khulna, Rajshahi"
        else:
            expected_cols = "code, description, unit, Zone-A, Zone-B, Zone-C, Zone-D"
        
        st.info(f"**Expected columns:** {expected_cols}")
        
        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=["csv"],
            help="CSV should have columns: code, description, unit, zone1, zone2, zone3, zone4"
        )
        
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.markdown("#### Preview (First 10 rows)")
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)
            
            # Validate columns
            if source == "PWD":
                required_cols = ['code', 'description', 'Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']
            else:
                required_cols = ['code', 'description', 'Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Missing columns: {missing_cols}")
            else:
                st.success("✅ CSV format is valid")
                
                if st.button("💾 Save to Database", type="primary", use_container_width=True, key="save_csv_to_db"):
                    self._save_csv_to_db(df, source, edition_year)


    def _parse_pasted_data(self, text, source, has_header=False):
        """Parse tab-separated pasted data"""
        lines = text.strip().split('\n')
        data = []
        
        start_idx = 1 if has_header else 0
        
        for i, line in enumerate(lines):
            if i < start_idx:
                continue
                
            if not line.strip():
                continue
            
            # Split by tab
            parts = line.split('\t')
            if len(parts) < 5:
                st.warning(f"Skipping line {i+1} (need at least 5 columns): {line[:50]}")
                continue
            
            try:
                code = parts[0].strip()
                description = parts[1].strip()
                unit = parts[2].strip() if len(parts) > 2 else ''
                
                # Determine parent code
                code_parts = code.split('.')
                if len(code_parts) >= 2:
                    parent_code = '.'.join(code_parts[:2])
                else:
                    parent_code = code
                
                if source == "PWD":
                    zone_names = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
                else:
                    zone_names = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
                
                row = {
                    'code': code,
                    'parent_code': parent_code,
                    'description': description,
                    'unit': unit,
                }
                
                for i, zone in enumerate(zone_names):
                    rate_idx = 3 + i
                    if rate_idx < len(parts):
                        # Remove commas and currency symbols
                        rate_str = parts[rate_idx].replace(',', '').replace('Tk', '').replace('৳', '').strip()
                        try:
                            row[zone] = float(rate_str) if rate_str else 0.0
                        except:
                            row[zone] = 0.0
                    else:
                        row[zone] = 0.0
                
                data.append(row)
            except Exception as e:
                st.warning(f"Error parsing line {i+1}: {line[:50]}... Error: {e}")
        
        if data:
            return pd.DataFrame(data)
        return None


    def _save_row_data_to_db(self, rows, source, edition_year):
        """Save row-by-row entered data to database"""
         # Double-check permission
        if not can_edit_rates():
            st.error("❌ You don't have permission to save rate data.")
            return
        try:
            if source == "PWD":
                self.db.init_pwd_hierarchical_tables()
            else:
                self.db.init_lged_tables()
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create version
            from datetime import date
            version_name = f"Manual Entry {source} {edition_year}"
            
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source, version_name, edition_year, date.today(), True, datetime.now(), 'manual_entry'))
            
            version_id = cursor.lastrowid
            
            # Collect unique parents
            parents_added = set()
            
            for row in rows:
                code = row['code']
                parent_code = row['parent_code']
                description = row['description']
                unit = row.get('unit', '')
                
                code_parts = code.split('.')
                chapter = code_parts[0]
                
                # Add parent if not already added
                if parent_code not in parents_added:
                    if source == "PWD":
                        cursor.execute("""
                            INSERT OR IGNORE INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                            VALUES (?, ?, ?, ?)
                        """, (parent_code, f"Parent of {parent_code}", chapter, version_id))
                    else:
                        cursor.execute("""
                            INSERT OR IGNORE INTO lged_parents (code, description, chapter_number, version_id)
                            VALUES (?, ?, ?, ?)
                        """, (parent_code, f"Parent of {parent_code}", chapter, version_id))
                    parents_added.add(parent_code)
                
                # Add child
                if source == "PWD":
                    cursor.execute("""
                        INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (code, parent_code, description, unit, edition_year, version_id))
                    
                    for zone in ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']:
                        rate = row.get(zone, 0)
                        if rate > 0:
                            cursor.execute("""
                                INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                                VALUES (?, ?, ?, ?, ?)
                            """, (code, zone, float(rate), edition_year, version_id))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO lged_children (code, parent_code, description, unit, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (code, parent_code, description, unit, edition_year, version_id))
                    
                    child_id = cursor.lastrowid
                    
                    for zone in ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']:
                        rate = row.get(zone, 0)
                        if rate > 0:
                            cursor.execute("""
                                INSERT INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                                VALUES (?, ?, ?, ?)
                            """, (child_id, zone, float(rate), version_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {len(rows)} items to {source} database!")
            st.balloons()
            
            # Clear rows
            st.session_state.manual_rows = []
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


    def _save_csv_to_db(self, df, source, edition_year):
        """Save CSV uploaded data to database"""
        
        # Convert dataframe to rows format
        rows = []
        
        if source == "PWD":
            zone_cols = ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']
        else:
            zone_cols = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']
        
        for _, row in df.iterrows():
            code = str(row['code'])
            code_parts = code.split('.')
            if len(code_parts) >= 2:
                parent_code = '.'.join(code_parts[:2])
            else:
                parent_code = code
            
            row_data = {
                'code': code,
                'parent_code': parent_code,
                'description': row['description'],
                'unit': row.get('unit', ''),
            }
            
            for zone in zone_cols:
                if zone in row:
                    try:
                        row_data[zone] = float(row[zone]) if pd.notna(row[zone]) else 0.0
                    except:
                        row_data[zone] = 0.0
                else:
                    row_data[zone] = 0.0
            
            rows.append(row_data)
        
        self._save_row_data_to_db(rows, source, edition_year)
    def render_edit_interface(self, source, edition_year):
        """Edit existing rate data"""
        
        st.markdown("### ✏️ Edit Existing Rates")
        st.caption("Search, select, and edit existing rate entries")
        
        # Load existing data
        if source == "PWD":
            data = self._load_pwd_edit_data()
            code_column = 'pwd_code'
            parent_column = 'parent_code'
            desc_column = 'description'
            zone_columns = ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']
        else:
            data = self._load_lged_edit_data()
            code_column = 'code'
            parent_column = 'parent_code'
            desc_column = 'description'
            zone_columns = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']
        
        if data.empty:
            st.info(f"No {source} data found to edit. Please add data first.")
            return
        
        # Search and filter
        st.markdown("#### 🔍 Search & Filter")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("Search by Code", placeholder="Enter item code...", key="edit_search_code")
        with col2:
            search_desc = st.text_input("Search by Description", placeholder="Enter description...", key="edit_search_desc")
        with col3:
            # Get unique parent codes for filtering
            parent_options = ["All"] + sorted(data[parent_column].unique().tolist())
            filter_parent = st.selectbox("Filter by Parent", parent_options, key="edit_filter_parent")
        
        # Apply filters
        filtered_data = data.copy()
        if search_term:
            filtered_data = filtered_data[filtered_data[code_column].str.contains(search_term, case=False, na=False)]
        if search_desc:
            filtered_data = filtered_data[filtered_data[desc_column].str.contains(search_desc, case=False, na=False)]
        if filter_parent != "All":
            filtered_data = filtered_data[filtered_data[parent_column] == filter_parent]
        
        st.markdown(f"**Found {len(filtered_data)} items**")
        
        # Select item to edit
        if not filtered_data.empty:
            # Create display options
            item_options = [f"{row[code_column]} - {row[desc_column][:60]}..." for _, row in filtered_data.iterrows()]
            selected_item = st.selectbox("Select item to edit", item_options, key="edit_select_item")
            
            if selected_item:
                # Get the selected row
                selected_code = selected_item.split(" - ")[0]
                selected_row = filtered_data[filtered_data[code_column] == selected_code].iloc[0]
                
                st.markdown("---")
                st.markdown("#### 📝 Edit Item")
                
                # Edit form
                with st.form("edit_item_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Code (read-only)
                        st.text_input("Item Code", value=selected_row[code_column], disabled=True)
                        
                        # Parent selection
                        all_parents = sorted(data[parent_column].unique().tolist())
                        current_parent = selected_row[parent_column]
                        parent_index = all_parents.index(current_parent) if current_parent in all_parents else 0
                        new_parent = st.selectbox("Parent Code", all_parents, index=parent_index)
                    
                    with col2:
                        # Unit
                        unit_options = ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"]
                        current_unit = selected_row.get('unit', '')
                        unit_index = unit_options.index(current_unit) if current_unit in unit_options else 0
                        new_unit = st.selectbox("Unit", unit_options, index=unit_index)
                    
                    # Description (editable)
                    new_description = st.text_area("Description", value=selected_row[desc_column], height=150)
                    
                    # Rates (editable)
                    st.markdown("##### Rates")
                    rate_cols = st.columns(4)
                    new_rates = {}
                    for i, zone in enumerate(zone_columns):
                        with rate_cols[i]:
                            current_rate = selected_row.get(zone, 0)
                            new_rates[zone] = st.number_input(zone, value=float(current_rate), step=100.0, format="%.2f", key=f"edit_rate_{zone}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                    with col2:
                        delete_clicked = st.form_submit_button("🗑️ Delete Item", use_container_width=True)
                    
                    if submitted:
                        success = self._update_existing_item(
                            source, selected_code, new_parent, new_description, new_unit, new_rates, edition_year
                        )
                        if success:
                            st.success(f"✅ Updated {selected_code}")
                            st.rerun()
                    
                    if delete_clicked:
                        if st.warning(f"Are you sure you want to delete {selected_code}?"):
                            success = self._delete_item(source, selected_code)
                            if success:
                                st.success(f"✅ Deleted {selected_code}")
                                st.rerun()
            
            # Bulk edit section
            st.markdown("---")
            with st.expander("📦 Bulk Operations", expanded=False):
                st.markdown("#### Bulk Update")
                
                col1, col2 = st.columns(2)
                with col1:
                    bulk_parent = st.selectbox("Set Parent for Selected", ["-- No Change --"] + all_parents if 'all_parents' in dir() else ["-- No Change --"])
                with col2:
                    bulk_unit = st.selectbox("Set Unit for Selected", ["-- No Change --", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"])
                
                # Multi-select for bulk operations
                bulk_items = st.multiselect(
                    "Select items to update",
                    options=[f"{row[code_column]} - {row[desc_column][:60]}..." for _, row in filtered_data.iterrows()],
                    key="bulk_items"
                )
                
                if bulk_items and st.button("Apply Bulk Update", key="apply_bulk_update"):
                    updated_count = 0
                    for item in bulk_items:
                        item_code = item.split(" - ")[0]
                        updates = {}
                        if bulk_parent != "-- No Change --":
                            updates['parent'] = bulk_parent
                        if bulk_unit != "-- No Change --":
                            updates['unit'] = bulk_unit
                        
                        if self._bulk_update_item(source, item_code, updates):
                            updated_count += 1
                    
                    st.success(f"✅ Updated {updated_count} items")
                    st.rerun()

    def _load_pwd_edit_data(self):
        """Load PWD data for editing"""
        try:
            conn = self.db.get_connection()
            query = """
                SELECT 
                    c.pwd_code,
                    c.parent_code,
                    c.description,
                    c.unit,
                    COALESCE(r_dhaka.unit_rate, 0) as Dhaka,
                    COALESCE(r_chittagong.unit_rate, 0) as Chattogram,
                    COALESCE(r_khulna.unit_rate, 0) as Khulna,
                    COALESCE(r_rajshahi.unit_rate, 0) as Rajshahi
                FROM pwd_children c
                LEFT JOIN pwd_rates r_dhaka ON c.pwd_code = r_dhaka.pwd_code AND r_dhaka.zone_name = 'Dhaka'
                LEFT JOIN pwd_rates r_chittagong ON c.pwd_code = r_chittagong.pwd_code AND r_chittagong.zone_name = 'Chattogram'
                LEFT JOIN pwd_rates r_khulna ON c.pwd_code = r_khulna.pwd_code AND r_khulna.zone_name = 'Khulna'
                LEFT JOIN pwd_rates r_rajshahi ON c.pwd_code = r_rajshahi.pwd_code AND r_rajshahi.zone_name = 'Rajshahi'
                ORDER BY c.pwd_code
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading PWD data: {e}")
            return pd.DataFrame()

    def _load_lged_edit_data(self):
        """Load LGED data for editing"""
        try:
            conn = self.db.get_connection()
            query = """
                SELECT 
                    c.code,
                    c.parent_code,
                    c.description,
                    c.unit,
                    COALESCE(MAX(CASE WHEN r.zone_name = 'Zone-A' THEN r.unit_rate END), 0) as 'Zone-A',
                    COALESCE(MAX(CASE WHEN r.zone_name = 'Zone-B' THEN r.unit_rate END), 0) as 'Zone-B',
                    COALESCE(MAX(CASE WHEN r.zone_name = 'Zone-C' THEN r.unit_rate END), 0) as 'Zone-C',
                    COALESCE(MAX(CASE WHEN r.zone_name = 'Zone-D' THEN r.unit_rate END), 0) as 'Zone-D'
                FROM lged_children c
                LEFT JOIN lged_zone_rates r ON c.id = r.child_id
                GROUP BY c.code, c.parent_code, c.description, c.unit
                ORDER BY c.code
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading LGED data: {e}")
            return pd.DataFrame()

    def _update_existing_item(self, source, code, new_parent, new_description, new_unit, new_rates, edition_year):
        """Update an existing item"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if source == "PWD":
                # Update child
                cursor.execute("""
                    UPDATE pwd_children 
                    SET parent_code = ?, description = ?, unit = ?, edition_year = ?
                    WHERE pwd_code = ?
                """, (new_parent, new_description, new_unit, edition_year, code))
                
                # Update rates
                for zone, rate in new_rates.items():
                    if rate > 0:
                        cursor.execute("""
                            INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year)
                            VALUES (?, ?, ?, ?)
                        """, (code, zone, rate, edition_year))
                    else:
                        cursor.execute("""
                            DELETE FROM pwd_rates WHERE pwd_code = ? AND zone_name = ?
                        """, (code, zone))
            else:
                # First get child_id
                cursor.execute("SELECT id FROM lged_children WHERE code = ?", (code,))
                result = cursor.fetchone()
                if result:
                    child_id = result[0]
                    
                    # Update child
                    cursor.execute("""
                        UPDATE lged_children 
                        SET parent_code = ?, description = ?, unit = ?, edition_year = ?
                        WHERE code = ?
                    """, (new_parent, new_description, new_unit, edition_year, code))
                    
                    # Update rates
                    for zone, rate in new_rates.items():
                        if rate > 0:
                            cursor.execute("""
                                INSERT OR REPLACE INTO lged_zone_rates (child_id, zone_name, unit_rate)
                                VALUES (?, ?, ?)
                            """, (child_id, zone, rate))
                        else:
                            cursor.execute("""
                                DELETE FROM lged_zone_rates WHERE child_id = ? AND zone_name = ?
                            """, (child_id, zone))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Error updating item: {e}")
            return False

    def _delete_item(self, source, code):
        """Delete an item"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if source == "PWD":
                # Delete rates first (foreign key)
                cursor.execute("DELETE FROM pwd_rates WHERE pwd_code = ?", (code,))
                # Delete child
                cursor.execute("DELETE FROM pwd_children WHERE pwd_code = ?", (code,))
            else:
                # Get child_id
                cursor.execute("SELECT id FROM lged_children WHERE code = ?", (code,))
                result = cursor.fetchone()
                if result:
                    child_id = result[0]
                    # Delete rates first
                    cursor.execute("DELETE FROM lged_zone_rates WHERE child_id = ?", (child_id,))
                    # Delete child
                    cursor.execute("DELETE FROM lged_children WHERE code = ?", (code,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Error deleting item: {e}")
            return False

    def _bulk_update_item(self, source, code, updates):
        """Bulk update an item"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if 'parent' in updates:
                if source == "PWD":
                    cursor.execute("UPDATE pwd_children SET parent_code = ? WHERE pwd_code = ?", (updates['parent'], code))
                else:
                    cursor.execute("UPDATE lged_children SET parent_code = ? WHERE code = ?", (updates['parent'], code))
            
            if 'unit' in updates:
                if source == "PWD":
                    cursor.execute("UPDATE pwd_children SET unit = ? WHERE pwd_code = ?", (updates['unit'], code))
                else:
                    cursor.execute("UPDATE lged_children SET unit = ? WHERE code = ?", (updates['unit'], code))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            return False                
def render_quick_entry(db):
    """Quick single-item entry form"""
    if not can_edit_rates():
        st.error("❌ You don't have permission to add rates.")
        return
    
    render_role_badge()

    st.markdown("### ⚡ Quick Single Item Entry")
    st.caption("Quickly add a single rate item - automatically handles parent-child relationships")
    
    with st.form("quick_entry_form"):
        source = st.selectbox("Source", ["PWD", "LGED"])
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025)
        
        col1, col2 = st.columns(2)
        
        with col1:
            code = st.text_input("Item Code", placeholder="01.1.1 or 1.01.01", help="Use dot notation (e.g., 01.1.1)")
            description = st.text_area("Description", height=100, placeholder="Full description of the item")
            
            # Auto-detect if this is a parent or child based on code
            code_parts = code.split('.') if code else []
            if len(code_parts) == 2:
                st.info("📁 This will be created as a **Parent item** (no rates)")
            elif len(code_parts) >= 3:
                st.info("👶 This will be created as a **Child item** (with rates)")
                parent_code = '.'.join(code_parts[:2])
                st.info(f"📌 Will be linked to parent: **{parent_code}**")
        
        with col2:
            unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"])
            
            # Show rate fields only for child items (3+ parts)
            if len(code_parts) >= 3:
                if source == "PWD":
                    zone_labels = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
                else:
                    zone_labels = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
                
                st.markdown("##### Rates")
                rates = {}
                rate_cols = st.columns(4)
                for i, label in enumerate(zone_labels):
                    with rate_cols[i]:
                        rates[label] = st.number_input(label, value=0.0, step=100.0, format="%.2f", key=f"quick_rate_{label}")
        
        submitted = st.form_submit_button("💾 Save Item", type="primary", use_container_width=True)
        
        if submitted and code and description:
            # Determine if parent or child
            code_parts = code.split('.')
            
            if len(code_parts) == 2:
                # This is a parent item (no rates)
                data = {
                    'parents': [{
                        'code': code,
                        'description': description,
                        'children_count': 0
                    }],
                    'children': []
                }
            else:
                # This is a child item
                parent_code = '.'.join(code_parts[:2])
                data = {
                    'parents': [],  # Parent might not exist yet
                    'children': [{
                        'code': code,
                        'parent_code': parent_code,
                        'description': description,
                        'unit': unit,
                        'rates': rates
                    }]
                }
                
                # Add parent if it doesn't exist (optional - could warn user)
                st.warning(f"Note: This will be saved under parent '{parent_code}'. Make sure the parent exists or add it separately.")
            
            manual_entry = ManualRateEntry(db)
            manual_entry._save_hierarchy_to_db(data, source, edition_year)

