# modules/rate_crud_forms.py

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from modules.rbac import (
    rbac, can_view_rates, can_edit_rates, can_delete_rates,
    can_import_rates, render_role_badge, require_permission,
    render_protected_button, render_protected_data_editor
)
from database.unified_db_manager import get_db_manager


class RateCRUDForms:
    """Simple CRUD forms for Zones, Chapters, Parents, Children, and Versions"""
    
    def __init__(self, db):
        self.db = db or get_db_manager()
    
    def _log_audit(self, action, entity_type, entity_id, old_data=None, new_data=None):
        """Log audit trail"""
        try:
            # Use the db's audit log method if available, otherwise use direct insert
            if hasattr(self.db, 'log_audit'):
                self.db.log_audit(
                    user_id=st.session_state.get('user_id', 0),
                    username=st.session_state.get('username', 'unknown'),
                    role=st.session_state.get('user_role', 'viewer'),
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    old_data=old_data,
                    new_data=new_data
                )
            else:
                # Fallback: direct insert
                self.db.execute("""
                    INSERT INTO rate_audit_log (user_id, username, role, action, entity_type, entity_id, old_data, new_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.get('user_id', 0),
                    st.session_state.get('username', 'unknown'),
                    st.session_state.get('user_role', 'viewer'),
                    action,
                    entity_type,
                    entity_id,
                    json.dumps(old_data) if old_data else None,
                    json.dumps(new_data) if new_data else None
                ))
            
            st.toast(f"📝 Audit: {st.session_state.get('username')} - {action} {entity_type}: {entity_id}")
        except Exception as e:
            st.warning(f"Audit log error: {e}")
    
    def _check_permission(self, permission):
        """
        Check if user has permission for rate management.
        Uses RBAC module for consistency.
        """
        user_role = st.session_state.get('user_role', 'viewer')
        
        # Admin users have full access
        if user_role in ['admin', 'system_admin']:
            return True
        
        # Use RBAC module for permission checks
        if permission == 'read':
            return can_view_rates()
        elif permission == 'update':
            return can_edit_rates()
        elif permission == 'delete':
            return can_delete_rates()
        elif permission == 'create':
            return can_import_rates() or can_edit_rates()
        
        return False

    def render(self):
        """Main interface with separate tabs for each CRUD operation"""
        
        # Check basic permission
        if not self._check_permission('read'):
            st.error("❌ You don't have permission to view this page")
            return
        
        user_role = st.session_state.get('user_role', 'viewer')
        company_id = st.session_state.get('company_id')
        
        # Render role badge
        render_role_badge()
        
        # Show subscription info if company user
        if company_id:
            from modules.subscription_manager import SubscriptionManager
            sub_manager = SubscriptionManager(self.db)
            sub = sub_manager.get_company_subscription(company_id)
            st.info(f"👤 Role: **{user_role.upper()}** | Plan: **{sub.get('plan_name', 'free')}** | "
                   f"✏️ Edit: {'✅' if can_edit_rates() else '❌'} | "
                   f"🗑️ Delete: {'✅' if can_delete_rates() else '❌'}")
        else:
            st.info(f"👤 Role: **{user_role.upper()}** | Permissions: {', '.join(self._get_user_permissions(user_role))}")
        
        st.markdown("""
        <div class="main-header">
            <h1>📝 Rate Management</h1>
            <p>Manage Zones, Chapters, Parents, Children, and Versions for PWD and LGED</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Source selection
        source = st.radio(
            "Select Rate Schedule",
            options=["PWD", "LGED"],
            horizontal=True,
            key="crud_source"
        )
        
        # Edition year
        edition_year = st.number_input(
            "Edition Year",
            min_value=2020,
            max_value=2030,
            value=2022 if source == "PWD" else 2025,
            key="crud_edition_year",
            help="Select which version/year these rates belong to"
        )
        
        # Debug mode toggle (only for admins)
        show_debug = False
        if user_role in ['admin', 'system_admin']:
            show_debug = st.checkbox("🐛 Show Debug Info", value=False, key="debug_mode")
        
        st.markdown("---")
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🗺️ Zones",
            "📚 Chapters",
            "📑 Sections",
            "📁 Parents",
            "👶 Children", 
            "📦 Versions"
        ])

        with tab1:
            self._zone_crud(source, show_debug)
        with tab2:
            self._chapter_crud(source, show_debug)
        with tab3:
            self._section_crud(source, show_debug)
        with tab4:
            self._parent_crud(source, edition_year, show_debug)
        with tab5:
            self._child_crud(source, edition_year, show_debug)
        with tab6:
            self._version_crud(source, show_debug)
    
    def _get_user_permissions(self, role):
        """Get permissions for a role"""
        permissions = {
            'admin': ['create', 'read', 'update', 'delete'],
            'system_admin': ['create', 'read', 'update', 'delete'],
            'company_admin': ['create', 'read', 'update', 'delete'],
            'manager': ['create', 'read', 'update'],
            'analyst': ['read', 'update'],
            'data_entry': ['create', 'read', 'update'],
            'viewer': ['read']
        }
        return permissions.get(role, ['read'])
    
    # ========== ZONE CRUD ==========
    def _zone_crud(self, source, show_debug=False):
        """Zone CRUD with editable table"""
        
        st.markdown("### 🗺️ Manage Zones")
        
        can_edit = self._check_permission('update')
        can_delete = self._check_permission('delete')
        
        if not can_edit:
            st.info("ℹ️ You have view-only access to zones")
        
        # Load existing zones using CRUD method
        zones = self.db.get_zones(source) if hasattr(self.db, 'get_zones') else self._get_zones_fallback(source)
        
        if zones:
            st.markdown("#### Existing Zones (Double-click to edit)")
            
            # Convert to DataFrame for editing
            df = pd.DataFrame([{
                'Code': z.get('code', ''),
                'Name': z.get('name', ''),
                'Description': z.get('description', ''),
                'Divisions': z.get('divisions', ''),
                'Accessibility Bonus %': z.get('accessibility_bonus', 0) * 100
            } for z in zones])
            
            # Debug info
            if show_debug:
                st.write(f"Debug: Loaded {len(zones)} zones from database")
            
            # Editable table
            if can_edit:
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    key="zone_editor",
                    column_config={
                        "Code": st.column_config.TextColumn("Code", disabled=True),
                        "Name": st.column_config.TextColumn("Name"),
                        "Description": st.column_config.TextColumn("Description", width="large"),
                        "Divisions": st.column_config.TextColumn("Divisions"),
                        "Accessibility Bonus %": st.column_config.NumberColumn("Bonus %", min_value=0, max_value=50, step=1)
                    }
                )
                
                # Check for changes and save
                if not edited_df.equals(df):
                    for idx in edited_df.index:
                        if not edited_df.loc[idx].equals(df.loc[idx]):
                            old_data = df.loc[idx].to_dict()
                            new_data = edited_df.loc[idx].to_dict()
                            
                            # Save changes using CRUD method
                            self.db.update_zone(
                                source=source,
                                code=edited_df.loc[idx, 'Code'],
                                name=edited_df.loc[idx, 'Name'],
                                description=edited_df.loc[idx, 'Description'],
                                divisions=edited_df.loc[idx, 'Divisions'],
                                bonus=edited_df.loc[idx, 'Accessibility Bonus %'] / 100
                            )
                            
                            self._log_audit('UPDATE', 'zone', edited_df.loc[idx, 'Code'], old_data, new_data)
                            
                            if show_debug:
                                st.success(f"✅ Updated zone: {edited_df.loc[idx, 'Code']}")
                    
                    st.rerun()
            else:
                # View-only display
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Add new zone (only if user has create permission)
        if self._check_permission('create'):
            with st.expander("➕ Add New Zone", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    zone_code = st.text_input("Zone Code", placeholder="A, B, C, D or Dhaka, Ctg", key="zone_code")
                    zone_name = st.text_input("Zone Name", placeholder="Dhaka & Mymensingh Division", key="zone_name")
                    accessibility_bonus = st.slider("Accessibility Bonus (%)", min_value=0, max_value=50, value=5, key="zone_bonus")
                
                with col2:
                    zone_description = st.text_area("Description", placeholder="Description of this zone", height=80, key="zone_description")
                    divisions = st.text_input("Covered Divisions", placeholder="Dhaka, Mymensingh", key="zone_divisions")
                
                if st.button("Add Zone", key="add_zone"):
                    if zone_code and zone_name:
                        self.db.save_zone(source, zone_code, zone_name, zone_description, divisions, accessibility_bonus / 100)
                        self._log_audit('CREATE', 'zone', zone_code, None, {'code': zone_code, 'name': zone_name})
                        st.success(f"✅ Added Zone: {zone_code} - {zone_name}")
                        if show_debug:
                            st.code(f"Inserted into database: zone_code={zone_code}")
                        st.rerun()
                    else:
                        st.error("Please fill Zone Code and Zone Name")
    
    def _get_zones_fallback(self, source):
        """Fallback method for zones if CRUD method not available"""
        try:
            conn = self.db.get_connection()
            if source == "PWD":
                zones = [
                    {'code': 'Dhaka', 'name': 'Dhaka & Mymensingh Division', 'description': 'Capital region', 
                    'divisions': 'Dhaka, Mymensingh', 'accessibility_bonus': 0},
                    {'code': 'Chattogram', 'name': 'Chattogram & Sylhet Division', 'description': 'Port city region', 
                    'divisions': 'Chattogram, Sylhet', 'accessibility_bonus': 0},
                    {'code': 'Khulna', 'name': 'Khulna & Barishal Division', 'description': 'South-western region', 
                    'divisions': 'Khulna, Barishal', 'accessibility_bonus': 0},
                    {'code': 'Rajshahi', 'name': 'Rajshahi & Rangpur Division', 'description': 'Northern region', 
                    'divisions': 'Rajshahi, Rangpur', 'accessibility_bonus': 0}
                ]
            else:
                results = self.db.query("""
                    SELECT zone_code as code, zone_name as name, divisions, accessibility_bonus, description 
                    FROM lged_zone_mapping 
                    ORDER BY zone_code
                """)
                zones = [
                    {
                        'code': r.get('code'),
                        'name': r.get('name'),
                        'divisions': r.get('divisions', ''),
                        'accessibility_bonus': r.get('accessibility_bonus', 0),
                        'description': r.get('description', '')
                    } for r in results
                ]
            return zones
        except Exception as e:
            if show_debug:
                st.error(f"Zone load error: {e}")
            return []
    
    # ========== CHAPTER CRUD ==========
    
    # modules/rate_crud_forms.py - Full _chapter_crud and _child_crud

    def _chapter_crud(self, source, show_debug):
        """Chapter CRUD with editable table"""
        
        st.markdown("### 📚 Manage Chapters")
        
        can_edit = self._check_permission('update')
        
        # Load existing chapters using CRUD method
        try:
            chapters = self.db.get_chapters(source) if hasattr(self.db, 'get_chapters') else []
        except Exception as e:
            if show_debug:
                st.error(f"Error loading chapters: {e}")
            chapters = []
        
        if not chapters:
            st.info(f"No chapters found for {source}. Add chapters below.")
            chapters = []
        
        if chapters:
            df = pd.DataFrame(chapters)
            # Ensure required columns exist
            for col in ['chapter_number', 'chapter_name', 'description']:
                if col not in df.columns:
                    df[col] = ''
            
            # Convert chapter_number to string for display
            if 'chapter_number' in df.columns:
                df['chapter_number'] = df['chapter_number'].astype(str)
            
            if show_debug:
                st.write(f"Debug: Loaded {len(df)} chapters from database")
            
            if not df.empty:
                st.markdown("#### Existing Chapters (Double-click to edit)")
                
                if can_edit:
                    edited_df = st.data_editor(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        key=f"chapter_editor_{source}",
                        column_config={
                            "chapter_number": st.column_config.TextColumn("Chapter Number", disabled=True),
                            "chapter_name": st.column_config.TextColumn("Chapter Name"),
                            "description": st.column_config.TextColumn("Description", width="large")
                        }
                    )
                    
                    # Check for changes
                    if not edited_df.equals(df):
                        for idx in edited_df.index:
                            if not edited_df.loc[idx].equals(df.loc[idx]):
                                old_name = df.loc[idx, 'chapter_name']
                                new_name = edited_df.loc[idx, 'chapter_name']
                                old_desc = df.loc[idx, 'description'] if 'description' in df.columns else ''
                                new_desc = edited_df.loc[idx, 'description'] if 'description' in edited_df.columns else ''
                                
                                # Update chapter using CRUD method
                                try:
                                    # Update chapter name
                                    if new_name != old_name:
                                        self.db.update_chapter(source, edited_df.loc[idx, 'chapter_number'], new_name)
                                    
                                    # Update description if method exists
                                    if hasattr(self.db, 'update_chapter_description') and new_desc != old_desc:
                                        self.db.update_chapter_description(source, edited_df.loc[idx, 'chapter_number'], new_desc)
                                    
                                    self._log_audit('UPDATE', 'chapter', edited_df.loc[idx, 'chapter_number'], 
                                                {'name': old_name, 'description': old_desc}, 
                                                {'name': new_name, 'description': new_desc})
                                    
                                    if show_debug:
                                        st.success(f"✅ Updated chapter: {edited_df.loc[idx, 'chapter_number']}")
                                except Exception as e:
                                    if show_debug:
                                        st.error(f"Error updating chapter: {e}")
                        
                        st.rerun()
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Add new chapter
        if self._check_permission('create'):
            with st.expander("➕ Add New Chapter", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    chapter_num = st.text_input("Chapter Number", placeholder="01 or 1", key=f"chapter_num_{source}")
                with col2:
                    chapter_name = st.text_input("Chapter Name", placeholder="Chapter Name", key=f"chapter_name_{source}")
                
                chapter_description = st.text_area("Description (Optional)", placeholder="Chapter description", key=f"chapter_desc_{source}", height=80)
                
                if st.button("Add Chapter", key=f"add_chapter_{source}"):
                    if chapter_num and chapter_name:
                        try:
                            self.db.save_chapter(source, chapter_num, chapter_name)
                            
                            # Save description if method exists
                            if hasattr(self.db, 'update_chapter_description'):
                                self.db.update_chapter_description(source, chapter_num, chapter_description)
                            
                            self._log_audit('CREATE', 'chapter', chapter_num, None, 
                                        {'number': chapter_num, 'name': chapter_name, 'description': chapter_description})
                            st.success(f"✅ Added Chapter {chapter_num}: {chapter_name}")
                            if show_debug:
                                st.code(f"Inserted into database: chapter_number={chapter_num}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding chapter: {e}")
                    else:
                        st.error("Please fill both fields")


    def _child_crud(self, source, edition_year, show_debug):
        """Child CRUD with editable table"""
        
        st.markdown("### 👶 Manage Child Items")
        
        can_edit = self._check_permission('update')
        
        # Load existing parents for dropdown
        try:
            parents = self.db.get_parents(source) if hasattr(self.db, 'get_parents') else []
        except Exception as e:
            if show_debug:
                st.error(f"Error loading parents: {e}")
            parents = []
        
        if not parents:
            st.warning("⚠️ No parents found. Please add parents first in the 'Parents' tab.")
            return
        
        # Load existing children using CRUD method
        try:
            children = self.db.get_children(source) if hasattr(self.db, 'get_children') else []
        except Exception as e:
            if show_debug:
                st.error(f"Error loading children: {e}")
            children = []
        
        if show_debug:
            st.write(f"Debug: Loaded {len(children)} children from database")
        
        # ========== DISPLAY EXISTING CHILDREN (if any) ==========
        if children:
            st.markdown("#### Existing Children (Double-click to edit)")
            
            # Get zone names with safe handling
            try:
                zones = self.db.get_zones(source) if hasattr(self.db, 'get_zones') else []
            except Exception as e:
                if show_debug:
                    st.error(f"Error loading zones: {e}")
                zones = []
            
            # Filter out zones with None or empty code
            valid_zones = [z for z in zones if z.get('code')]
            zone_names = [z.get('code', '') for z in valid_zones]
            
            # Build DataFrame
            data = []
            for child in children:
                row = {
                    'Code': child.get('code', ''),
                    'Parent': child.get('parent_code', ''),
                    'Description': child.get('description', ''),
                    'Unit': child.get('unit', '')
                }
                for zone in zone_names:
                    if zone:  # Only add if zone name is not empty
                        row[zone] = child.get('rates', {}).get(zone, 0)
                data.append(row)
            
            if data:
                df = pd.DataFrame(data)
                
                # Ensure all rate columns are numeric
                for zone in zone_names:
                    if zone and zone in df.columns:
                        df[zone] = pd.to_numeric(df[zone], errors='coerce').fillna(0)
                
                # Create column config
                column_config = {
                    "Code": st.column_config.TextColumn("Code", disabled=True),
                    "Parent": st.column_config.SelectboxColumn("Parent", options=[p.get('code', '') for p in parents if p.get('code')]),
                    "Description": st.column_config.TextColumn("Description", width="large"),
                    "Unit": st.column_config.SelectboxColumn("Unit", options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"])
                }
                
                # Add zone columns with safe keys
                for zone in zone_names:
                    if zone:  # Only add if zone name is not empty
                        column_config[zone] = st.column_config.NumberColumn(
                            f"{zone}", 
                            format="%.2f",
                            step=100.0,
                            help=f"Rate for {zone} zone"
                        )
                
                if can_edit:
                    edited_df = st.data_editor(
                        df,
                        column_config=column_config,
                        use_container_width=True,
                        hide_index=True,
                        key=f"child_editor_{source}"
                    )
                    
                    # Check for changes
                    if not edited_df.equals(df):
                        for idx in edited_df.index:
                            if not edited_df.loc[idx].equals(df.loc[idx]):
                                old_data = df.loc[idx].to_dict()
                                new_data = edited_df.loc[idx].to_dict()
                                
                                # Get rates for this child with safe zone names
                                rates = {}
                                for zone in zone_names:
                                    if zone:  # Only add if zone name is not empty
                                        rates[zone] = edited_df.loc[idx].get(zone, 0)
                                
                                try:
                                    self.db.save_child(
                                        source=source,
                                        child_code=edited_df.loc[idx, 'Code'],
                                        parent_code=edited_df.loc[idx, 'Parent'],
                                        description=edited_df.loc[idx, 'Description'],
                                        unit=edited_df.loc[idx, 'Unit'],
                                        edition_year=edition_year,
                                        rates=rates
                                    )
                                    
                                    self._log_audit('UPDATE', 'child', edited_df.loc[idx, 'Code'], old_data, new_data)
                                    
                                    if show_debug:
                                        st.success(f"✅ Updated child: {edited_df.loc[idx, 'Code']}")
                                except Exception as e:
                                    if show_debug:
                                        st.error(f"Error updating child: {e}")
                        
                        st.rerun()
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No valid child data to display.")
        
        else:
            st.info("No child items found. Use the form below to add new child items.")
        
        st.markdown("---")
        
        # ========== ADD NEW CHILD ==========
        st.markdown("#### ➕ Add New Child Item")
        
        with st.form(f"add_child_form_{source}", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                child_code = st.text_input("Child Code", placeholder="01.1.1 or 1.01.01", key=f"child_code_{source}")
                
                # Parent selection dropdown
                parent_options = ["-- Select Parent --"] + [f"{p.get('code', '')} - {p.get('description', '')[:50]}..." for p in parents if p.get('code')]
                selected_parent = st.selectbox("Select Parent", parent_options, key=f"child_parent_{source}")
                
                if selected_parent != "-- Select Parent --":
                    parent_code = selected_parent.split(" - ")[0]
                    if child_code and not child_code.startswith(parent_code):
                        st.warning(f"⚠️ Child code should start with '{parent_code}'")
                else:
                    parent_code = ""
                
                unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key=f"child_unit_{source}")
            
            with col2:
                child_desc = st.text_area("Description", placeholder="Item description", height=100, key=f"child_desc_{source}")
            
            # Rate fields with safe zone handling
            try:
                zones = self.db.get_zones(source) if hasattr(self.db, 'get_zones') else []
            except Exception as e:
                if show_debug:
                    st.error(f"Error loading zones: {e}")
                zones = []
            
            # Filter out zones with None or empty code
            valid_zones = [z for z in zones if z.get('code')]
            
            if valid_zones:
                st.markdown("##### Rates by Zone")
                
                # Use columns only for valid zones
                rate_cols = st.columns(len(valid_zones))
                rates = {}
                for i, zone in enumerate(valid_zones):
                    zone_code = zone.get('code', '')
                    zone_name = zone.get('name', zone_code)
                    # Use zone_code as the key, ensure it's not None
                    safe_key = f"new_child_rate_{zone_code}_{source}" if zone_code else f"new_child_rate_{i}_{source}"
                    with rate_cols[i]:
                        rates[zone_code] = st.number_input(
                            f"{zone_name}", 
                            value=0.0, 
                            step=100.0, 
                            format="%.2f", 
                            key=safe_key
                        )
            else:
                st.warning("⚠️ No zones available. Please add zones first in the 'Zones' tab.")
                rates = {}
            
            submitted = st.form_submit_button("➕ Add Child Item", use_container_width=True)
            
            if submitted and child_code and child_desc and parent_code:
                if not child_code.startswith(parent_code):
                    st.error(f"Child code must start with parent code '{parent_code}'")
                else:
                    try:
                        # Save to database using CRUD method
                        self.db.save_child(
                            source=source,
                            child_code=child_code,
                            parent_code=parent_code,
                            description=child_desc,
                            unit=unit,
                            edition_year=edition_year,
                            rates=rates
                        )
                        
                        self._log_audit('CREATE', 'child', child_code, None, {
                            'code': child_code, 
                            'parent': parent_code,
                            'description': child_desc,
                            'unit': unit,
                            'rates': rates
                        })
                        st.success(f"✅ Added Child: {child_code} under parent {parent_code}")
                        if show_debug:
                            st.code(f"Inserted into database: child_code={child_code}, parent={parent_code}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving child: {e}")
            elif submitted:
                st.error("Please fill all required fields (Code, Description, and Parent)")
                
    # ========== SECTION CRUD ==========
    def _section_crud(self, source, show_debug=False):
        """LGED Section CRUD with editable table"""
        
        if source != "LGED":
            st.info("ℹ️ Sections are only applicable for LGED rate schedules")
            return
        
        st.markdown("### 📑 Manage LGED Sections")
        st.caption("Sections are sub-categories within chapters (e.g., 3.01 - Box Cutting)")
        
        can_edit = self._check_permission('update')
        
        if not can_edit:
            st.info("ℹ️ Sections are view-only. Contact system admin for modifications.")
        
        # First, select a chapter
        st.markdown("#### Step 1: Select Chapter")
        
        try:
            chapters = self.db.get_chapters("LGED") if hasattr(self.db, 'get_chapters') else []
        except Exception as e:
            st.error(f"Error loading chapters: {e}")
            chapters = []
        
        if not chapters:
            st.warning("⚠️ No LGED chapters found. Please add chapters first in the 'Chapters' tab.")
            return
        
        chapter_options = []
        for ch in chapters:
            chapter_num = str(ch.get('chapter_number', ''))
            chapter_name = ch.get('chapter_name', '')
            if chapter_num:
                chapter_options.append(f"{chapter_num} - {chapter_name}")
        
        if not chapter_options:
            st.warning("⚠️ No valid chapters found.")
            return
        
        selected_chapter = st.selectbox(
            "Select Chapter",
            options=chapter_options,
            key="section_chapter_select"
        )
        
        if selected_chapter:
            chapter_num = selected_chapter.split(" - ")[0]
            
            st.markdown(f"#### Step 2: Sections for Chapter {chapter_num}")
            
            # 🔍 DEBUG: Show that we're querying
            if show_debug:
                st.write(f"🔍 Querying sections for chapter: {chapter_num}")
            
            # Load existing sections using CRUD method
            try:
                sections = self.db.get_sections_for_chapter(chapter_num) if hasattr(self.db, 'get_sections_for_chapter') else []
            except Exception as e:
                if show_debug:
                    st.error(f"Error loading sections: {e}")
                sections = []
            
            # 🔍 DEBUG: Show raw data
            if show_debug:
                st.write(f"🔍 Found {len(sections)} sections for chapter {chapter_num}")
                if sections:
                    st.write("🔍 First section:", sections[0] if sections else "None")
                    st.write("🔍 All sections:", sections)
                else:
                    st.warning("⚠️ No sections returned from database!")
                    # Try direct query to debug
                    try:
                        direct_result = self.db.query("""
                            SELECT id, section_number, section_name, description, display_order
                            FROM lged_sections 
                            WHERE chapter_number = ?
                            ORDER BY display_order, section_number
                        """, (chapter_num,))
                        st.write(f"🔍 Direct query result: {direct_result}")
                    except Exception as e:
                        st.write(f"🔍 Direct query error: {e}")
            
            if sections:
                # Build DataFrame
                df_data = []
                for s in sections:
                    df_data.append({
                        'Section Number': str(s.get('section_number', '')),
                        'Section Name': s.get('section_name', ''),
                        'Description': s.get('description', ''),
                        'Display Order': s.get('display_order', 0)
                    })
                
                df = pd.DataFrame(df_data)
                
                if not df.empty:
                    if can_edit:
                        edited_df = st.data_editor(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            key=f"section_editor_{chapter_num}",
                            column_config={
                                "Section Number": st.column_config.TextColumn("Section Number", disabled=True, width="small"),
                                "Section Name": st.column_config.TextColumn("Section Name", width="medium"),
                                "Description": st.column_config.TextColumn("Description", width="large"),
                                "Display Order": st.column_config.NumberColumn("Order", min_value=0, max_value=999, step=1, width="small")
                            }
                        )
                        
                        # Check for changes
                        if not edited_df.equals(df):
                            for idx in edited_df.index:
                                if not edited_df.loc[idx].equals(df.loc[idx]):
                                    try:
                                        self.db.update_section(
                                            chapter_num,
                                            edited_df.loc[idx, 'Section Number'],
                                            edited_df.loc[idx, 'Section Name'],
                                            edited_df.loc[idx, 'Description'],
                                            edited_df.loc[idx, 'Display Order']
                                        )
                                        if show_debug:
                                            st.success(f"✅ Updated section: {edited_df.loc[idx, 'Section Number']}")
                                    except Exception as e:
                                        if show_debug:
                                            st.error(f"Error updating section: {e}")
                            st.rerun()
                    else:
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No valid section data to display.")
            else:
                st.info(f"No sections found for Chapter {chapter_num}. Add sections below.")
            
            # Add new section (admin only)
            if self._check_permission('create'):
                with st.expander("➕ Add New Section", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        auto_number = st.checkbox("Auto-generate", value=True, key=f"auto_section_num_{chapter_num}")
                        if auto_number:
                            try:
                                next_section_num = self.db.get_next_section_number(chapter_num) if hasattr(self.db, 'get_next_section_number') else f"{chapter_num}.01"
                            except:
                                next_section_num = f"{chapter_num}.01"
                            section_number = st.text_input("Section Number", value=next_section_num, disabled=True, key=f"section_num_{chapter_num}")
                        else:
                            section_number = st.text_input("Section Number", placeholder=f"{chapter_num}.01", key=f"section_num_manual_{chapter_num}")
                        section_name = st.text_input("Section Name", placeholder="e.g., Box Cutting", key=f"section_name_{chapter_num}")
                    
                    with col2:
                        section_description = st.text_area("Description", height=100, key=f"section_desc_{chapter_num}")
                        display_order = st.number_input("Display Order", min_value=0, max_value=999, value=0, key=f"section_order_{chapter_num}")
                    
                    if st.button("Add Section", key=f"add_section_{chapter_num}"):
                        if section_number and section_name:
                            if self._validate_lged_section_number(section_number, chapter_num):
                                try:
                                    self.db.save_section(chapter_num, section_number, section_name, section_description, display_order)
                                    self._log_audit('CREATE', 'section', section_number, None, {
                                        'chapter': chapter_num,
                                        'number': section_number,
                                        'name': section_name,
                                        'description': section_description
                                    })
                                    st.success(f"✅ Added Section: {section_number}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error saving section: {e}")
                            else:
                                st.error(f"Section number must be format: {chapter_num}.XX")
                        else:
                            st.error("Please fill required fields")

    
    def _validate_lged_section_number(self, section_number: str, chapter_num: str) -> bool:
        """Validate LGED section number format (e.g., 3.01, 3.02, 3.10)"""
        if not section_number or '.' not in section_number:
            return False
        
        parts = section_number.split('.')
        if len(parts) != 2:
            return False
        
        # Check if chapter number matches
        if parts[0] != chapter_num:
            return False
        
        # Check if second part is valid two-digit number (01-99)
        try:
            section_part = int(parts[1])
            return 1 <= section_part <= 99
        except ValueError:
            return False
    
    # ========== PARENT CRUD ==========
    def _parent_crud(self, source, edition_year, show_debug):
        """Parent CRUD with editable table"""
        
        st.markdown("### 📁 Manage Parents")
        
        can_edit = self._check_permission('update')
        
        # Load existing parents using CRUD method
        parents = self.db.get_parents(source) if hasattr(self.db, 'get_parents') else []
        
        if show_debug:
            st.write(f"Debug: Loaded {len(parents)} parents from database")
        
        if parents:
            st.markdown("#### Existing Parents (Double-click to edit)")
            
            # Build DataFrame
            df_data = []
            for p in parents:
                row = {
                    'Code': p.get('code', ''),
                    'Chapter': p.get('chapter_number', ''),
                    'Description': p.get('description', '')
                }
                if source == "LGED":
                    row['Section'] = p.get('section_number', '')
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            if can_edit:
                # Get chapters for dropdown
                chapters = self.db.get_chapters(source) if hasattr(self.db, 'get_chapters') else []
                chapter_options = [ch.get('chapter_number', '') for ch in chapters] if chapters else []
                
                if source == "PWD":
                    column_config = {
                        "Code": st.column_config.TextColumn("Code", disabled=True),
                        "Chapter": st.column_config.SelectboxColumn("Chapter", options=chapter_options) if chapter_options else st.column_config.TextColumn("Chapter"),
                        "Description": st.column_config.TextColumn("Description", width="large")
                    }
                else:  # LGED
                    section_options = [""]
                    if not df.empty and df.iloc[0]['Chapter']:
                        sections = self.db.get_sections_for_chapter(str(df.iloc[0]['Chapter'])) if hasattr(self.db, 'get_sections_for_chapter') else []
                        section_options = [""] + [s.get('section_number', '') for s in sections] if sections else [""]
                    
                    column_config = {
                        "Code": st.column_config.TextColumn("Code", disabled=True),
                        "Chapter": st.column_config.SelectboxColumn("Chapter", options=chapter_options) if chapter_options else st.column_config.TextColumn("Chapter"),
                        "Section": st.column_config.SelectboxColumn("Section", options=section_options),
                        "Description": st.column_config.TextColumn("Description", width="large")
                    }
                
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    key="parent_editor",
                    column_config=column_config
                )
                
                # Check for changes
                if not edited_df.equals(df):
                    for idx in edited_df.index:
                        if not edited_df.loc[idx].equals(df.loc[idx]):
                            old_data = df.loc[idx].to_dict()
                            new_data = edited_df.loc[idx].to_dict()
                            
                            section_value = edited_df.loc[idx].get('Section', '') if 'Section' in edited_df.columns else ''
                            self.db.update_parent(
                                source=source,
                                parent_code=edited_df.loc[idx, 'Code'],
                                description=edited_df.loc[idx, 'Description'],
                                chapter=edited_df.loc[idx, 'Chapter'],
                                section=section_value
                            )
                            
                            self._log_audit('UPDATE', 'parent', edited_df.loc[idx, 'Code'], old_data, new_data)
                            
                            if show_debug:
                                st.success(f"✅ Updated parent: {edited_df.loc[idx, 'Code']}")
                    
                    st.rerun()
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Add new parent
        if self._check_permission('create'):
            with st.expander("➕ Add New Parent", expanded=False):
                if source == "PWD":
                    chapters = self.db.get_chapters(source) if hasattr(self.db, 'get_chapters') else []
                else:
                    chapters = self.db.get_chapters(source) if hasattr(self.db, 'get_chapters') else []
                
                chapter_options = ["-- Select Chapter --"]
                chapter_map = {}
                for ch in chapters:
                    display_text = f"{ch.get('chapter_number', '')} - {ch.get('chapter_name', '')}"
                    chapter_options.append(display_text)
                    chapter_map[display_text] = ch.get('chapter_number', '')
                
                col1, col2 = st.columns(2)
                with col1:
                    parent_code = st.text_input("Parent Code", placeholder="01.1 or 1.01", key="parent_code")
                    selected_chapter = st.selectbox("Chapter", chapter_options, key="parent_chapter")
                    if selected_chapter != "-- Select Chapter --":
                        parent_chapter = chapter_map.get(selected_chapter, '')
                    else:
                        parent_chapter = ""
                    
                    # Section selection for LGED
                    parent_section = ""
                    if source == "LGED" and parent_chapter:
                        sections = self.db.get_sections_for_chapter(parent_chapter) if hasattr(self.db, 'get_sections_for_chapter') else []
                        if sections:
                            section_options = ["-- No Section --"] + [s.get('section_number', '') for s in sections]
                            selected_section = st.selectbox("Section (Optional)", section_options, key="parent_section")
                            if selected_section != "-- No Section --":
                                parent_section = selected_section
                
                with col2:
                    parent_desc = st.text_area("Parent Description", placeholder="Full description of the parent item", height=100, key="parent_desc")
                
                if st.button("Add Parent", key="add_parent"):
                    if parent_code and parent_desc and parent_chapter:
                        self.db.save_parent(source, parent_code, parent_desc, parent_chapter, parent_section)
                        self._log_audit('CREATE', 'parent', parent_code, None, {
                            'code': parent_code, 
                            'description': parent_desc,
                            'chapter': parent_chapter,
                            'section': parent_section
                        })
                        st.success(f"✅ Added Parent: {parent_code}")
                        if show_debug:
                            st.code(f"Inserted into database: parent_code={parent_code}")
                        st.rerun()
                    else:
                        st.error("Please fill all required fields (Code, Chapter, Description)")
    
    # ========== VERSION CRUD ==========
    def _version_crud(self, source, show_debug):
        """Version CRUD with audit log"""
        
        st.markdown("### 📦 Manage Versions")
        
        can_edit = self._check_permission('update')
        
        # Load versions using CRUD method
        versions = self.db.get_versions(source) if hasattr(self.db, 'get_versions') else []
        
        if show_debug:
            st.write(f"Debug: Loaded {len(versions)} versions from database")
        
        if versions:
            st.markdown("#### Existing Versions")
            df = pd.DataFrame(versions)
            if not df.empty and 'is_active' in df.columns:
                df['is_active'] = df['is_active'].apply(lambda x: "✅ Active" if x else "📦 Archived")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Set active version (only for users with update permission)
            if can_edit:
                st.markdown("---")
                st.markdown("#### Set Active Version")
                version_options = {str(v.get('id')): f"{v.get('version_name', 'Unknown')} ({v.get('edition_year', 'N/A')})" 
                                  for v in versions}
                version_to_activate = st.selectbox(
                    "Select Version to Activate",
                    options=list(version_options.keys()) if version_options else [],
                    format_func=lambda x: version_options.get(x, "Unknown"),
                    key="activate_version"
                )
                
                if version_to_activate and st.button("Set as Active", key="confirm_activate"):
                    if self.db.activate_version(int(version_to_activate), source):
                        self._log_audit('ACTIVATE', 'version', str(version_to_activate), None, {'version_id': version_to_activate})
                        st.success("✅ Version activated!")
                        if show_debug:
                            st.code(f"Activated version ID: {version_to_activate}")
                        st.rerun()
                    else:
                        st.error("Failed to activate version")
        
        # Add new version
        if self._check_permission('create'):
            with st.expander("➕ Add New Version", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    version_name = st.text_input("Version Name", placeholder=f"{source} Schedule 2025", key="version_name")
                    edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025, key="version_year")
                with col2:
                    effective_date = st.date_input("Effective From", value=datetime.now().date(), key="version_date")
                    is_active = st.checkbox("Set as Active Version", value=True, key="version_active")
                
                if st.button("Add Version", key="add_version"):
                    if version_name and edition_year:
                        success = self.db.save_version(
                            source=source,
                            version_name=version_name,
                            edition_year=edition_year,
                            effective_date=effective_date.isoformat(),
                            is_active=is_active,
                            created_by=st.session_state.get('username', 'admin')
                        )
                        
                        if success:
                            self._log_audit('CREATE', 'version', version_name, None, 
                                          {'name': version_name, 'year': edition_year, 'active': is_active})
                            st.success(f"✅ Added Version: {version_name} ({edition_year})")
                            if show_debug:
                                st.code(f"Inserted version: {version_name}, year={edition_year}")
                            st.rerun()
                        else:
                            st.warning(f"Version for {source} {edition_year} already exists!")
                    else:
                        st.error("Please fill version name and year")


# Convenience function
def render_rate_crud_forms(db):
    forms = RateCRUDForms(db)
    forms.render()