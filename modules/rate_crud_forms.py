# modules/rate_crud_forms.py

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import hashlib
from functools import lru_cache
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
        self._cache = {}
    
    # ========== CACHING HELPERS ==========
    @st.cache_data(ttl=300)
    def _get_cached_chapters(_self, source: str):
        """Cache chapters data"""
        try:
            return _self.db.get_chapters(source) if hasattr(_self.db, 'get_chapters') else []
        except Exception:
            return []
    
    @st.cache_data(ttl=300)
    def _get_cached_parents(_self, source: str):
        """Cache parents data"""
        try:
            return _self.db.get_parents(source) if hasattr(_self.db, 'get_parents') else []
        except Exception:
            return []
    
    @st.cache_data(ttl=300)
    def _get_cached_children(_self, source: str):
        """Cache children data"""
        try:
            return _self.db.get_children(source) if hasattr(_self.db, 'get_children') else []
        except Exception:
            return []
    
    @st.cache_data(ttl=300)
    def _get_cached_zones(_self, source: str):
        """Cache zones data"""
        try:
            return _self.db.get_zones(source) if hasattr(_self.db, 'get_zones') else []
        except Exception:
            return []
    
    @st.cache_data(ttl=300)
    def _get_cached_versions(_self, source: str):
        """Cache versions data"""
        try:
            return _self.db.get_versions(source) if hasattr(_self.db, 'get_versions') else []
        except Exception:
            return []
    
    @st.cache_data(ttl=300)
    def _get_cached_sections(_self, chapter_num: str):
        """Cache sections data"""
        try:
            return _self.db.get_sections_for_chapter(chapter_num) if hasattr(_self.db, 'get_sections_for_chapter') else []
        except Exception:
            return []
    
    def _clear_cache(self):
        """Clear all cached data"""
        for method in ['_get_cached_chapters', '_get_cached_parents', '_get_cached_children', 
                       '_get_cached_zones', '_get_cached_versions', '_get_cached_sections']:
            if hasattr(self, method):
                getattr(self, method).clear()
    
    def _log_audit_with_duplicate_check(self, action, entity_type, entity_id, old_data=None, new_data=None):
        """Log audit trail with duplicate prevention"""
        try:
            # Generate a hash based on the operation details
            audit_data = f"{action}_{entity_type}_{entity_id}_{json.dumps(old_data)}_{json.dumps(new_data)}"
            audit_hash = hashlib.md5(audit_data.encode()).hexdigest()
            
            # Check if this audit was already logged
            if not hasattr(st.session_state, '_audit_hashes'):
                st.session_state._audit_hashes = set()
            
            if audit_hash in st.session_state._audit_hashes:
                return
            
            user_id = st.session_state.get('user_id', 0)
            username = st.session_state.get('username', 'unknown')
            role = st.session_state.get('user_role', 'viewer')
            
            # Direct insert - all columns are nullable, so this always works
            self.db.execute("""
                INSERT INTO rate_audit_log 
                (user_id, username, role, action, entity_type, entity_id, old_data, new_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                role,
                action,
                entity_type,
                entity_id,
                json.dumps(old_data) if old_data else None,
                json.dumps(new_data) if new_data else None
            ))
            
            st.session_state._audit_hashes.add(audit_hash)
            
            # Limit the set size to prevent memory issues
            if len(st.session_state._audit_hashes) > 200:
                st.session_state._audit_hashes = set(list(st.session_state._audit_hashes)[-100:])
            
            st.toast(f"📝 Audit: {username} - {action} {entity_type}: {entity_id}")
        except Exception as e:
            print(f"Audit log error: {e}")
    
    def _log_audit(self, action, entity_type, entity_id, old_data=None, new_data=None):
        """Log audit trail"""
        try:
            user_id = st.session_state.get('user_id', 0)
            username = st.session_state.get('username', 'unknown')
            role = st.session_state.get('user_role', 'viewer')
            
            self.db.execute("""
                INSERT INTO rate_audit_log 
                (user_id, username, role, action, entity_type, entity_id, old_data, new_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                role,
                action,
                entity_type,
                entity_id,
                json.dumps(old_data) if old_data else None,
                json.dumps(new_data) if new_data else None
            ))
            
            st.toast(f"📝 Audit: {username} - {action} {entity_type}: {entity_id}")
        except Exception as e:
            print(f"Audit log error: {e}")
    
    def _check_permission(self, permission):
        """Check if user has permission for rate management."""
        user_role = st.session_state.get('user_role', 'viewer')
        
        if user_role in ['admin', 'system_admin']:
            return True
        
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
        
        if not self._check_permission('read'):
            st.error("❌ You don't have permission to view this page")
            return
        
        user_role = st.session_state.get('user_role', 'viewer')
        company_id = st.session_state.get('company_id')
        
        render_role_badge()
        
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
        
        source = st.radio(
            "Select Rate Schedule",
            options=["PWD", "LGED"],
            horizontal=True,
            key="crud_source"
        )
        
        edition_year = st.number_input(
            "Edition Year",
            min_value=2020,
            max_value=2030,
            value=2022 if source == "PWD" else 2025,
            key="crud_edition_year",
            help="Select which version/year these rates belong to"
        )
        
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
            self.render_line_items(source, edition_year, show_debug)
        with tab6:
            self._version_crud(source, show_debug)
    
    def _get_user_permissions(self, role):
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
        
        if not can_edit:
            st.info("ℹ️ You have view-only access to zones")
        
        # ✅ Use cached zones
        zones = self._get_cached_zones(source)
        
        if zones:
            st.markdown("#### Existing Zones (Double-click to edit)")
            
            # Build DataFrame efficiently
            df_data = []
            append = df_data.append
            for z in zones:
                append({
                    'Code': z.get('code', ''),
                    'Name': z.get('name', ''),
                    'Description': z.get('description', ''),
                    'Divisions': z.get('divisions', ''),
                    'Accessibility Bonus %': z.get('accessibility_bonus', 0) * 100
                })
            df = pd.DataFrame(df_data)
            
            if show_debug:
                st.write(f"Debug: Loaded {len(zones)} zones from database")
            
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
                
                if not edited_df.equals(df):
                    for idx in edited_df.index:
                        if not edited_df.loc[idx].equals(df.loc[idx]):
                            old_data = df.loc[idx].to_dict()
                            new_data = edited_df.loc[idx].to_dict()
                            
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
                    
                    self._clear_cache()
                    st.rerun()
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        
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
                        self._clear_cache()
                        st.rerun()
                    else:
                        st.error("Please fill Zone Code and Zone Name")
    
    def _get_zones_fallback(self, source):
        """Fallback method for zones if CRUD method not available"""
        try:
            if source == "PWD":
                return [
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
                return [
                    {
                        'code': r.get('code'),
                        'name': r.get('name'),
                        'divisions': r.get('divisions', ''),
                        'accessibility_bonus': r.get('accessibility_bonus', 0),
                        'description': r.get('description', '')
                    } for r in results
                ]
        except Exception:
            return []
    
    # ========== CHAPTER CRUD ==========
    def _chapter_crud(self, source, show_debug):
        """Chapter CRUD with editable table"""
        
        st.markdown("### 📚 Manage Chapters")
        
        can_edit = self._check_permission('update')
        
        # ✅ Use cached chapters
        chapters = self._get_cached_chapters(source)
        
        if not chapters:
            st.info(f"No chapters found for {source}. Add chapters below.")
        
        if chapters:
            df = pd.DataFrame(chapters)
            # Ensure required columns exist
            for col in ['chapter_number', 'chapter_name', 'description']:
                if col not in df.columns:
                    df[col] = ''
            
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
                    
                    if not edited_df.equals(df):
                        # Generate a hash of the changes to detect duplicates
                        changes_hash = hashlib.md5(
                            json.dumps(edited_df.to_dict()).encode()
                        ).hexdigest()
                        
                        if not hasattr(st.session_state, '_chapter_processed'):
                            st.session_state._chapter_processed = set()
                        
                        if changes_hash not in st.session_state._chapter_processed:
                            st.session_state._chapter_processed.add(changes_hash)
                            
                            for idx in edited_df.index:
                                if not edited_df.loc[idx].equals(df.loc[idx]):
                                    old_data = df.loc[idx].to_dict()
                                    new_data = edited_df.loc[idx].to_dict()
                                    
                                    try:
                                        chapter_num = str(edited_df.loc[idx, 'chapter_number'])
                                        
                                        if new_data.get('chapter_name') != old_data.get('chapter_name'):
                                            self.db.update_chapter(
                                                source, 
                                                chapter_num, 
                                                edited_df.loc[idx, 'chapter_name']
                                            )
                                        
                                        if hasattr(self.db, 'update_chapter_description'):
                                            if new_data.get('description') != old_data.get('description'):
                                                self.db.update_chapter_description(
                                                    source, 
                                                    chapter_num, 
                                                    edited_df.loc[idx, 'description']
                                                )
                                        
                                        self._log_audit_with_duplicate_check(
                                            'UPDATE', 
                                            'chapter', 
                                            chapter_num, 
                                            old_data, 
                                            new_data
                                        )
                                        
                                        if show_debug:
                                            st.success(f"✅ Updated chapter: {chapter_num}")
                                            
                                    except Exception as e:
                                        if show_debug:
                                            st.error(f"Error updating chapter: {e}")
                            
                            self._clear_cache()
                            st.rerun()
                        else:
                            if show_debug:
                                st.info("⏭️ Skipping duplicate chapter update")
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
        
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
                            
                            if hasattr(self.db, 'update_chapter_description'):
                                self.db.update_chapter_description(source, chapter_num, chapter_description)
                            
                            self._log_audit_with_duplicate_check(
                                'CREATE', 
                                'chapter', 
                                chapter_num, 
                                None, 
                                {'number': chapter_num, 'name': chapter_name, 'description': chapter_description}
                            )
                            
                            st.success(f"✅ Added Chapter {chapter_num}: {chapter_name}")
                            if show_debug:
                                st.code(f"Inserted into database: chapter_number={chapter_num}")
                            self._clear_cache()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding chapter: {e}")
                    else:
                        st.error("Please fill both fields")

    def render_line_items(self, source: str, edition_year: int, show_debug: bool = False):
        """Render line items (children) with spreadsheet-style grid view"""
        
        # Determine source type
        is_lged = source.upper() == 'LGED'
        is_pwd = source.upper() == 'PWD'
        
        st.markdown("### 📋 Line Items Management")
        
        if is_lged:
            st.caption("📋 **LGED Structure:** Chapter → Section → Parent → Child → Rates")
        else:
            st.caption("📋 **PWD Structure:** Chapter → Parent → Child → Rates")
        
        can_edit = self._check_permission('update')
        
        # ===== GET DATA =====
        if is_lged:
            parents = self._get_cached_lged_parents(source)
        else:
            parents = self._get_cached_parents(source)
        
        if not parents:
            st.warning("⚠️ No parents found. Please add parents first.")
            return
        
        children = self._get_cached_children(source)
        zones = self._get_cached_zones(source)
        valid_zones = [z for z in zones if z.get('code')]
        zone_names = [z.get('code', '') for z in valid_zones]
        
        if show_debug:
            st.write(f"Debug: Loaded {len(children)} children from database")
        
        # ===== HEADER WITH ACTIONS =====
        col1, col2, col3, col4, col5 = st.columns([1, 1.5, 1.5, 1.5, 0.8])
        
        with col1:
            if st.button("➕ Add Line Item", key=f"line_add_{source}", type="primary", use_container_width=True):
                st.session_state[f'editing_child_{source}'] = None
                st.session_state[f'show_add_child_{source}'] = not st.session_state.get(f'show_add_child_{source}', False)
                st.rerun()
        
        with col2:
            # Chapter filter
            chapters = set()
            for child in children:
                if child.get('chapter_number'):
                    chapters.add(str(child.get('chapter_number')))
            
            chapter_options = ["All"] + sorted(list(chapters)) if chapters else ["All"]
            selected_chapter = st.selectbox(
                "📚 Chapter",
                options=chapter_options,
                key=f"line_chapter_filter_{source}",
                label_visibility="collapsed"
            )
        
        with col3:
            # Parent filter (or Section for LGED)
            if is_lged:
                sections = set()
                for child in children:
                    if child.get('section_number'):
                        sections.add(str(child.get('section_number')))
                section_options = ["All Sections"] + sorted(list(sections)) if sections else ["All Sections"]
                selected_filter = st.selectbox(
                    "📑 Section",
                    options=section_options,
                    key=f"line_section_filter_{source}",
                    label_visibility="collapsed"
                )
            else:
                parent_codes = [p.get('code', '') for p in parents if p.get('code')]
                parent_options = ["All Parents"] + sorted(parent_codes) if parent_codes else ["All Parents"]
                selected_filter = st.selectbox(
                    "👪 Parent",
                    options=parent_options,
                    key=f"line_parent_filter_{source}",
                    label_visibility="collapsed"
                )
        
        with col4:
            search_term = st.text_input(
                "🔍 Search",
                placeholder="Code or description...",
                key=f"line_search_{source}",
                label_visibility="collapsed"
            )
        
        with col5:
            st.session_state[f'line_per_page_{source}'] = st.selectbox(
                "Rows",
                options=[5, 10, 25, 50, 100],
                index=[5, 10, 25, 50, 100].index(st.session_state.get(f'line_per_page_{source}', 10)),
                key=f"line_per_page_select_{source}",
                label_visibility="collapsed"
            )
        
        st.divider()
        
        # ===== APPLY FILTERS =====
        filtered_children = children.copy()
        
        if selected_chapter != "All":
            filtered_children = [
                c for c in filtered_children 
                if str(c.get('chapter_number', '')) == selected_chapter
            ]
        
        if is_lged and selected_filter != "All Sections":
            filtered_children = [
                c for c in filtered_children 
                if str(c.get('section_number', '')) == selected_filter
            ]
        elif not is_lged and selected_filter != "All Parents":
            filtered_children = [
                c for c in filtered_children 
                if c.get('parent_code', '') == selected_filter
            ]
        
        if search_term:
            search_lower = search_term.lower()
            filtered_children = [
                c for c in filtered_children
                if search_lower in str(c.get('code', '')).lower()
                or search_lower in str(c.get('description', '')).lower()
            ]
        
        total = len(filtered_children)
        
        if show_debug:
            st.write(f"Debug: Filtered to {total} children")
        
        if not filtered_children:
            st.info("No line items found matching the filters.")
            return
        
        # ===== METRICS =====
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", total)
        with col2:
            # Count items with rates
            items_with_rates = sum(1 for c in filtered_children if c.get('rates') and any(c.get('rates', {}).values()))
            st.metric("With Rates", items_with_rates)
        with col3:
            # Count unique parents
            unique_parents = len(set(c.get('parent_code', '') for c in filtered_children if c.get('parent_code')))
            st.metric("Parents", unique_parents)
        with col4:
            # Count unique chapters
            unique_chapters = len(set(str(c.get('chapter_number', '')) for c in filtered_children if c.get('chapter_number')))
            st.metric("Chapters", unique_chapters)
        
        st.markdown("---")
        
        # ===== BUILD DATAFRAME =====
        df_data = []
        for child in filtered_children:
            row = {
                'code': child.get('code', ''),
                'parent': child.get('parent_code', ''),
                'description': child.get('description', ''),
                'unit': child.get('unit', ''),
                'chapter': child.get('chapter_number', ''),
            }
            
            # LGED: Add section
            if is_lged:
                row['section'] = child.get('section_number', '')
            
            # Add rates
            rates = child.get('rates', {})
            for zone in zone_names:
                if zone:
                    row[zone] = rates.get(zone, 0)
            
            # Add hidden fields for editing
            row['_child_data'] = child
            
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        
        # Format zone columns
        for zone in zone_names:
            if zone in df.columns:
                df[zone] = pd.to_numeric(df[zone], errors='coerce').fillna(0)
        
        # ===== SORT =====
        if f'line_sort_col_{source}' not in st.session_state:
            st.session_state[f'line_sort_col_{source}'] = 'code'
        if f'line_sort_asc_{source}' not in st.session_state:
            st.session_state[f'line_sort_asc_{source}'] = True
        
        sort_col = st.session_state.get(f'line_sort_col_{source}', 'code')
        sort_asc = st.session_state.get(f'line_sort_asc_{source}', True)
        
        if sort_col in df.columns:
            df = df.sort_values(by=sort_col, ascending=sort_asc)
            df = df.reset_index(drop=True)
        
        # ===== DISPLAY COLUMNS =====
        display_cols = ['code', 'parent', 'description', 'unit', 'chapter']
        if is_lged:
            display_cols.insert(3, 'section')
        display_cols.extend(zone_names)
        
        # Create display DataFrame
        display_df = df[display_cols].copy()
        
        # Format zone columns for display
        for zone in zone_names:
            if zone in display_df.columns:
                display_df[zone] = display_df[zone].apply(
                    lambda x: f"{x:,.2f}" if x and x != 0 else ''
                )
        
        # ===== STYLING =====
        def color_zone(val):
            if val and val != '':
                try:
                    num_val = float(val.replace(',', ''))
                    if num_val > 10000:
                        return 'color: #065f46; background-color: #d1fae5; font-weight: bold;'
                    elif num_val > 5000:
                        return 'color: #92400e; background-color: #fef3c7;'
                    elif num_val > 1000:
                        return 'color: #1e40af; background-color: #dbeafe;'
                    else:
                        return 'color: #475569;'
                except:
                    pass
            return ''
        
        styled_df = display_df.style
        
        # Apply zone coloring
        for zone in zone_names:
            if zone in display_df.columns:
                styled_df = styled_df.map(color_zone, subset=[zone])
        
        # ===== DISPLAY DATAFRAME =====
        column_config = {
            "code": st.column_config.Column("Code", width="small"),
            "parent": st.column_config.Column("Parent", width="small"),
            "description": st.column_config.Column("Description", width="large"),
            "unit": st.column_config.Column("Unit", width="small"),
            "chapter": st.column_config.Column("Chapter", width="small"),
        }
        
        if is_lged:
            column_config["section"] = st.column_config.Column("Section", width="small")
        
        for zone in zone_names:
            if zone:
                column_config[zone] = st.column_config.Column(zone, width="small")
        
        event = st.dataframe(
            styled_df,
            selection_mode="single-row",
            on_select="rerun",
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
        
        # ===== HANDLE SELECTION =====
        if event.selection and event.selection['rows']:
            selected_idx = event.selection['rows'][0]
            if selected_idx < len(df):
                row_data = df.iloc[selected_idx]
                child_data = row_data.get('_child_data')
                if child_data:
                    st.session_state[f'selected_child_{source}'] = child_data
                    st.session_state[f'selected_child_code_{source}'] = row_data.get('code')
                    st.session_state[f'show_child_detail_{source}'] = True
                    st.rerun()
        
        # ===== DETAIL VIEW =====
        if st.session_state.get(f'show_child_detail_{source}', False):
            child_data = st.session_state.get(f'selected_child_{source}')
            child_code = st.session_state.get(f'selected_child_code_{source}')
            
            if child_data:
                st.markdown("---")
                st.markdown(f"### 📋 Detail View: {child_code}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Code:** {child_data.get('code', 'N/A')}")
                    st.markdown(f"**Parent:** {child_data.get('parent_code', 'N/A')}")
                    st.markdown(f"**Unit:** {child_data.get('unit', 'N/A')}")
                    st.markdown(f"**Chapter:** {child_data.get('chapter_number', 'N/A')}")
                    if is_lged:
                        st.markdown(f"**Section:** {child_data.get('section_number', 'N/A')}")
                
                with col2:
                    st.markdown("**Description:**")
                    st.markdown(f"_{child_data.get('description', 'N/A')}_")
                
                # Display rates
                rates = child_data.get('rates', {})
                if rates:
                    st.markdown("**Zone Rates:**")
                    rate_data = []
                    for zone in zone_names:
                        if zone:
                            rate_data.append({
                                'Zone': zone,
                                'Rate': f"৳{rates.get(zone, 0):,.2f}" if rates.get(zone, 0) else 'N/A'
                            })
                    st.dataframe(pd.DataFrame(rate_data), use_container_width=True, hide_index=True)
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("✏️ Edit", key=f"edit_line_{source}_{child_code}", use_container_width=True):
                        st.session_state[f'editing_child_{source}'] = child_data
                        st.session_state[f'edit_child_code_{source}'] = child_code
                        st.session_state[f'show_child_detail_{source}'] = False
                        st.rerun()
                
                with col2:
                    if can_edit and st.button("🗑️ Delete", key=f"delete_line_{source}_{child_code}", use_container_width=True):
                        try:
                            self.db.delete_child(source, child_code)
                            self._log_audit('DELETE', 'child', child_code, None, None)
                            st.success(f"✅ Deleted: {child_code}")
                            st.session_state[f'show_child_detail_{source}'] = False
                            st.session_state[f'selected_child_{source}'] = None
                            self._clear_cache()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting: {e}")
                
                with col3:
                    if st.button("❌ Close", key=f"close_line_detail_{source}", use_container_width=True):
                        st.session_state[f'show_child_detail_{source}'] = False
                        st.session_state[f'selected_child_{source}'] = None
                        st.rerun()
        
        # ===== PAGINATION =====
        per_page = st.session_state.get(f'line_per_page_{source}', 10)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        if f'line_page_{source}' not in st.session_state:
            st.session_state[f'line_page_{source}'] = 1
        
        if st.session_state[f'line_page_{source}'] > total_pages and total_pages > 0:
            st.session_state[f'line_page_{source}'] = total_pages
        
        start_idx = (st.session_state[f'line_page_{source}'] - 1) * per_page
        end_idx = min(start_idx + per_page, total)
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
        
        with col1:
            st.caption(f"Showing {start_idx + 1}–{end_idx} of {total} items")
        
        with col2:
            if st.button("◀ Prev", key=f"line_prev_{source}", disabled=(st.session_state[f'line_page_{source}'] <= 1), use_container_width=True):
                st.session_state[f'line_page_{source}'] -= 1
                st.rerun()
        
        with col3:
            if st.button("Next ▶", key=f"line_next_{source}", disabled=(st.session_state[f'line_page_{source}'] >= total_pages), use_container_width=True):
                st.session_state[f'line_page_{source}'] += 1
                st.rerun()
        
        with col4:
            jump_to = st.number_input(
                "Jump to page",
                min_value=1,
                max_value=total_pages if total_pages > 0 else 1,
                value=st.session_state[f'line_page_{source}'],
                step=1,
                key=f"line_jump_to_{source}",
                label_visibility="collapsed"
            )
            if jump_to != st.session_state[f'line_page_{source}'] and 1 <= jump_to <= total_pages:
                st.session_state[f'line_page_{source}'] = jump_to
                st.rerun()
        
        # ===== ADD FORM =====
        if st.session_state.get(f'show_add_child_{source}', False):
            st.markdown("---")
            st.markdown("### ➕ Add New Line Item")
            self._render_add_child_form(source, edition_year, valid_zones, is_lged, parents)
        
        # ===== EDIT FORM =====
        if st.session_state.get(f'editing_child_{source}'):
            self._render_child_edit_form(source, edition_year, valid_zones, is_lged, parents)


    def _child_crud(self, source, edition_year, show_debug):
        """Child CRUD with editable table - Supports both PWD and LGED"""
        
        # Determine source type
        is_lged = source.upper() == 'LGED'
        is_pwd = source.upper() == 'PWD'
        
        st.markdown("### 👶 Manage Child Items")
        
        if is_lged:
            st.info("📋 **LGED Structure:** Chapter → Section → Parent → Child → Rates")
        else:
            st.info("📋 **PWD Structure:** Chapter → Parent → Child → Rates")
        
        can_edit = self._check_permission('update')
        
        # ✅ Get parents (different for PWD vs LGED)
        if is_lged:
            parents = self._get_cached_lged_parents(source)
        else:
            parents = self._get_cached_parents(source)
        
        if not parents:
            st.warning("⚠️ No parents found. Please add parents first in the 'Parents' tab.")
            return
        
        # ✅ Get children
        children = self._get_cached_children(source)
        
        if show_debug:
            st.write(f"Debug: Loaded {len(children)} children from database")
        
        if children:
            # ========== FILTERS ==========
            st.markdown("#### 🔍 Filters")
            
            # Determine number of filter columns
            if is_lged:
                col1, col2, col3, col4 = st.columns(4)
            else:
                col1, col2, col3 = st.columns(3)
            
            # Extract unique chapters
            chapters = set()
            for child in children:
                if child.get('chapter_number'):
                    chapters.add(str(child.get('chapter_number')))
            
            with col1:
                if chapters:
                    chapter_options = ["All"] + sorted(list(chapters))
                    selected_chapter = st.selectbox(
                        "📚 Chapter",
                        options=chapter_options,
                        key=f"child_chapter_filter_{source}"
                    )
                else:
                    selected_chapter = "All"
                    st.info("No chapter data")
            
            with col2:
                # ✅ LGED: Section filter
                if is_lged:
                    sections = set()
                    for child in children:
                        if child.get('section_number'):
                            sections.add(str(child.get('section_number')))
                    
                    if sections:
                        section_options = ["All Sections"] + sorted(list(sections))
                        selected_section = st.selectbox(
                            "📑 Section",
                            options=section_options,
                            key=f"child_section_filter_{source}"
                        )
                    else:
                        selected_section = "All Sections"
                        st.info("No section data")
                else:
                    # PWD: Parent filter
                    parent_codes = [p.get('code', '') for p in parents if p.get('code')]
                    if parent_codes:
                        parent_options = ["All Parents"] + sorted(parent_codes)
                        selected_parent_filter = st.selectbox(
                            "👪 Parent",
                            options=parent_options,
                            key=f"child_parent_filter_{source}"
                        )
                    else:
                        selected_parent_filter = "All Parents"
            
            # LGED: Parent filter (in column 3)
            if is_lged:
                with col3:
                    parent_codes = [p.get('code', '') for p in parents if p.get('code')]
                    if parent_codes:
                        parent_options = ["All Parents"] + sorted(parent_codes)
                        selected_parent_filter = st.selectbox(
                            "👪 Parent",
                            options=parent_options,
                            key=f"child_parent_filter_{source}"
                        )
                    else:
                        selected_parent_filter = "All Parents"
            
            # Search filter (last column)
            search_col = col4 if is_lged else col3
            with search_col:
                search_term = st.text_input(
                    "🔍 Search",
                    placeholder="Code or description...",
                    key=f"child_search_{source}"
                )
            
            # ========== APPLY FILTERS ==========
            filtered_children = children.copy()
            
            # Chapter filter
            if selected_chapter != "All":
                filtered_children = [
                    c for c in filtered_children 
                    if str(c.get('chapter_number', '')) == selected_chapter
                ]
            
            # Section filter (LGED only)
            if is_lged and selected_section != "All Sections":
                filtered_children = [
                    c for c in filtered_children 
                    if str(c.get('section_number', '')) == selected_section
                ]
            
            # Parent filter
            if selected_parent_filter != "All Parents":
                filtered_children = [
                    c for c in filtered_children 
                    if c.get('parent_code', '') == selected_parent_filter
                ]
            
            # Search filter
            if search_term:
                search_lower = search_term.lower()
                filtered_children = [
                    c for c in filtered_children
                    if search_lower in str(c.get('code', '')).lower()
                    or search_lower in str(c.get('description', '')).lower()
                ]
            
            if show_debug:
                st.write(f"Debug: Filtered to {len(filtered_children)} children")
            
            if not filtered_children:
                st.warning(f"No children found matching the filters")
                return
            
            st.markdown("#### Existing Children (Click on a row to view/edit details)")
            
            zones = self._get_cached_zones(source)
            valid_zones = [z for z in zones if z.get('code')]
            zone_names = [z.get('code', '') for z in valid_zones]
            
            # ========== BUILD DATAFRAME ==========
            data = []
            append = data.append
            for child in filtered_children:
                row = {
                    'Code': child.get('code', ''),
                    'Parent': child.get('parent_code', ''),
                    'Description': child.get('description', '')[:80] + '...' if len(child.get('description', '')) > 80 else child.get('description', ''),
                    'Unit': child.get('unit', ''),
                    'Chapter': child.get('chapter_number', ''),
                    '_full_description': child.get('description', ''),
                    '_child_data': child
                }
                
                # ✅ LGED: Add Section column
                if is_lged:
                    row['Section'] = child.get('section_number', '')
                
                rates = child.get('rates', {})
                for zone in zone_names:
                    if zone:
                        row[zone] = rates.get(zone, 0)
                append(row)
            
            if data:
                df = pd.DataFrame(data)
                
                for zone in zone_names:
                    if zone and zone in df.columns:
                        df[zone] = pd.to_numeric(df[zone], errors='coerce').fillna(0)
                
                # Display columns
                display_cols = ['Code', 'Parent', 'Description', 'Unit', 'Chapter']
                if is_lged:
                    display_cols.insert(3, 'Section')  # Insert Section after Parent
                display_cols.extend(zone_names)
                
                display_df = df[display_cols].copy()
                
                # Format zone columns
                for zone in zone_names:
                    if zone in display_df.columns:
                        display_df[zone] = display_df[zone].apply(lambda x: f"৳{x:,.2f}" if x and x != 0 else '')
                
                # ========== ROW SELECTION ==========
                st.markdown("""
                <style>
                .row-clickable:hover {
                    background-color: #f0f2f6 !important;
                    cursor: pointer;
                }
                .row-selected {
                    background-color: #e6f3ff !important;
                    border-left: 4px solid #1f77b4;
                }
                </style>
                """, unsafe_allow_html=True)
                
                if f'selected_child_{source}' not in st.session_state:
                    st.session_state[f'selected_child_{source}'] = None
                
                # Display rows with clickable selection
                for idx, row in display_df.iterrows():
                    # Determine column layout based on source
                    if is_lged:
                        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.3, 1.0, 1.0, 2.5, 0.8, 0.8, 0.8])
                    else:
                        col1, col2, col3, col4, col5, col6 = st.columns([0.3, 1.2, 2.5, 0.8, 0.8, 0.8])
                    
                    with col1:
                        is_selected = st.checkbox(
                            "",
                            key=f"child_select_{source}_{idx}",
                            value=(st.session_state.get(f'selected_child_{source}') == idx)
                        )
                        if is_selected:
                            st.session_state[f'selected_child_{source}'] = idx
                        elif st.session_state.get(f'selected_child_{source}') == idx and not is_selected:
                            st.session_state[f'selected_child_{source}'] = None
                    
                    with col2:
                        st.markdown(f"**{row['Code']}**")
                    
                    with col3:
                        st.markdown(row['Description'])
                    
                    with col4:
                        st.markdown(row['Unit'])
                    
                    with col5:
                        st.markdown(f"📚 {row['Chapter']}")
                    
                    # LGED: Section column
                    if is_lged:
                        with col6:
                            st.markdown(f"📑 {row['Section']}")
                    
                    # Zone rate (quick preview) - show Zone-A in last column
                    if is_lged:
                        with col7:
                            zone_a = row.get('Zone-A', '')
                            st.markdown(f"💰 {zone_a}" if zone_a else "💰 -")
                    else:
                        with col6:
                            zone_a = row.get('Zone-A', '')
                            st.markdown(f"💰 {zone_a}" if zone_a else "💰 -")
                    
                    # ========== DETAIL VIEW ==========
                    if st.session_state.get(f'selected_child_{source}') == idx:
                        with st.expander(f"📊 Details for {row['Code']}", expanded=True):
                            child_data = df.iloc[idx]['_child_data']
                            full_description = df.iloc[idx]['_full_description']
                            
                            st.markdown(f"**Full Description:** {full_description}")
                            
                            # Show additional info based on source
                            if is_lged:
                                st.markdown(f"**Section:** {child_data.get('section_number', 'N/A')}")
                            st.markdown(f"**Chapter:** {child_data.get('chapter_number', 'N/A')}")
                            st.markdown(f"**Parent:** {child_data.get('parent_code', 'N/A')}")
                            
                            # Display all rates
                            st.markdown("**Zone Rates:**")
                            rate_data = []
                            for zone in zone_names:
                                if zone in df.columns:
                                    rate_value = df.iloc[idx][zone]
                                    rate_data.append({
                                        'Zone': zone,
                                        'Rate': f"৳{rate_value:,.2f}" if rate_value and rate_value != 0 else 'N/A'
                                    })
                            
                            if rate_data:
                                st.dataframe(pd.DataFrame(rate_data), use_container_width=True, hide_index=True)
                            
                            # Action buttons
                            col_edit1, col_edit2 = st.columns(2)
                            
                            with col_edit1:
                                if st.button(f"✏️ Edit {row['Code']}", key=f"edit_child_{source}_{idx}", use_container_width=True):
                                    st.session_state[f'editing_child_{source}'] = child_data
                                    st.session_state[f'edit_child_code_{source}'] = row['Code']
                                    st.rerun()
                            
                            with col_edit2:
                                if can_edit and st.button(f"🗑️ Delete {row['Code']}", key=f"delete_child_{source}_{idx}", use_container_width=True):
                                    try:
                                        self.db.delete_child(source, row['Code'])
                                        self._log_audit('DELETE', 'child', row['Code'], None, None)
                                        st.success(f"✅ Deleted child: {row['Code']}")
                                        self._clear_cache()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error deleting child: {e}")
                    
                    st.markdown("---")
                
                # ========== BULK EDIT ==========
                if can_edit and st.button("✏️ Edit Selected Child", use_container_width=True):
                    selected_idx = st.session_state.get(f'selected_child_{source}')
                    if selected_idx is not None and selected_idx < len(df):
                        child_data = df.iloc[selected_idx]['_child_data']
                        st.session_state[f'editing_child_{source}'] = child_data
                        st.session_state[f'edit_child_code_{source}'] = df.iloc[selected_idx]['Code']
                        st.rerun()
                    else:
                        st.warning("Please select a child first by clicking the checkbox on the left.")
                
                # ========== EDIT FORM ==========
                if st.session_state.get(f'editing_child_{source}'):
                    self._render_child_edit_form(source, edition_year, valid_zones, is_lged, parents)
                
                # ========== EXPORT ==========
                if st.button("📥 Export Filtered Children", use_container_width=True):
                    export_df = display_df.copy()
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        f"children_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
        
        st.markdown("---")
        
        # ========== ADD NEW CHILD FORM ==========
        self._render_add_child_form(source, edition_year, valid_zones, is_lged, parents)


    def _render_child_edit_form(self, source, edition_year, valid_zones, is_lged, parents):
        """Render the child edit form (handles both PWD and LGED)"""
        
        child_to_edit = st.session_state.get(f'editing_child_{source}')
        edit_code = st.session_state.get(f'edit_child_code_{source}')
        
        st.markdown("---")
        st.markdown(f"### ✏️ Editing Child: {edit_code}")
        
        with st.form(f"edit_child_form_{source}"):
            col1, col2 = st.columns(2)
            
            with col1:
                edit_code = st.text_input("Child Code", value=child_to_edit.get('code', ''), disabled=True, key=f"edit_code_{source}")
                
                parent_options = ["-- Select Parent --"] + [f"{p.get('code', '')} - {p.get('description', '')[:50]}..." for p in parents if p.get('code')]
                current_parent = child_to_edit.get('parent_code', '')
                default_parent_index = 0
                for i, opt in enumerate(parent_options):
                    if opt.startswith(current_parent):
                        default_parent_index = i
                        break
                selected_parent = st.selectbox("Parent", parent_options, index=default_parent_index, key=f"edit_parent_{source}")
                if selected_parent != "-- Select Parent --":
                    parent_code = selected_parent.split(" - ")[0]
                else:
                    parent_code = ""
                
                unit = st.selectbox(
                    "Unit",
                    ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"],
                    index=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"].index(child_to_edit.get('unit', '')),
                    key=f"edit_unit_{source}"
                )
                
                # Chapter input
                chapter_value = child_to_edit.get('chapter_number', '')
                edit_chapter = st.text_input("Chapter", value=str(chapter_value) if chapter_value else '', key=f"edit_chapter_{source}")
            
            with col2:
                edit_desc = st.text_area("Description", value=child_to_edit.get('description', ''), height=100, key=f"edit_desc_{source}")
                
                # ✅ LGED: Section input
                if is_lged:
                    section_value = child_to_edit.get('section_number', '')
                    edit_section = st.text_input("Section", value=str(section_value) if section_value else '', key=f"edit_section_{source}")
            
            # Zone rates
            if valid_zones:
                st.markdown("##### Rates by Zone")
                rate_cols = st.columns(len(valid_zones))
                edit_rates = {}
                current_rates = child_to_edit.get('rates', {})
                for i, zone in enumerate(valid_zones):
                    zone_code = zone.get('code', '')
                    zone_name = zone.get('name', zone_code)
                    with rate_cols[i]:
                        edit_rates[zone_code] = st.number_input(
                            f"{zone_name}",
                            value=float(current_rates.get(zone_code, 0)),
                            step=100.0,
                            format="%.2f",
                            key=f"edit_rate_{zone_code}_{source}"
                        )
            else:
                st.warning("⚠️ No zones available.")
                edit_rates = {}
            
            col_edit1, col_edit2, col_edit3 = st.columns(3)
            
            with col_edit1:
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    try:
                        # Build update data
                        update_data = {
                            'code': edit_code,
                            'parent_code': parent_code,
                            'description': edit_desc,
                            'unit': unit,
                            'edition_year': edition_year,
                            'rates': edit_rates,
                            'chapter_number': edit_chapter if edit_chapter else None
                        }
                        
                        # ✅ LGED: Add section
                        if is_lged:
                            update_data['section_number'] = edit_section if edit_section else None
                        
                        self.db.save_child(source=source, **update_data)
                        
                        self._log_audit('UPDATE', 'child', edit_code, child_to_edit, update_data)
                        st.success(f"✅ Updated child: {edit_code}")
                        st.session_state[f'editing_child_{source}'] = None
                        st.session_state[f'edit_child_code_{source}'] = None
                        self._clear_cache()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating child: {e}")
            
            with col_edit2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state[f'editing_child_{source}'] = None
                    st.session_state[f'edit_child_code_{source}'] = None
                    st.rerun()
            
            with col_edit3:
                if st.form_submit_button("🗑️ Delete", use_container_width=True):
                    try:
                        self.db.delete_child(source, edit_code)
                        self._log_audit('DELETE', 'child', edit_code, None, None)
                        st.success(f"✅ Deleted child: {edit_code}")
                        st.session_state[f'editing_child_{source}'] = None
                        st.session_state[f'edit_child_code_{source}'] = None
                        self._clear_cache()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting child: {e}")


    def _render_add_child_form(self, source, edition_year, valid_zones, is_lged, parents):
        """Render the add child form (handles both PWD and LGED)"""
        
        st.markdown("#### ➕ Add New Child Item")
        
        with st.form(f"add_child_form_{source}", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                child_code = st.text_input("Child Code", placeholder="01.1.1 or 1.01.01", key=f"child_code_{source}")
                
                parent_options = ["-- Select Parent --"] + [f"{p.get('code', '')} - {p.get('description', '')[:50]}..." for p in parents if p.get('code')]
                selected_parent = st.selectbox("Select Parent", parent_options, key=f"child_parent_{source}")
                
                if selected_parent != "-- Select Parent --":
                    parent_code = selected_parent.split(" - ")[0]
                    if child_code and not child_code.startswith(parent_code):
                        st.warning(f"⚠️ Child code should start with '{parent_code}'")
                else:
                    parent_code = ""
                
                unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key=f"child_unit_{source}")
                
                # Chapter input
                chapter_number = st.text_input("Chapter", placeholder="e.g., 01, 02, 26", key=f"child_chapter_{source}")
                
                # ✅ LGED: Section input
                if is_lged:
                    section_number = st.text_input("Section", placeholder="e.g., 3.01, 3.02", key=f"child_section_{source}")
            
            with col2:
                child_desc = st.text_area("Description", placeholder="Item description", height=100, key=f"child_desc_{source}")
            
            # Zone rates
            if valid_zones:
                st.markdown("##### Rates by Zone")
                rate_cols = st.columns(len(valid_zones))
                rates = {}
                for i, zone in enumerate(valid_zones):
                    zone_code = zone.get('code', '')
                    zone_name = zone.get('name', zone_code)
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
                st.warning("⚠️ No zones available.")
                rates = {}
            
            submitted = st.form_submit_button("➕ Add Child Item", use_container_width=True)
            
            if submitted and child_code and child_desc and parent_code:
                if not child_code.startswith(parent_code):
                    st.error(f"Child code must start with parent code '{parent_code}'")
                else:
                    try:
                        # Build child data
                        child_data = {
                            'code': child_code,
                            'parent_code': parent_code,
                            'description': child_desc,
                            'unit': unit,
                            'edition_year': edition_year,
                            'rates': rates,
                            'chapter_number': chapter_number if chapter_number else None
                        }
                        
                        # ✅ LGED: Add section
                        if is_lged:
                            child_data['section_number'] = section_number if section_number else None
                        
                        self.db.save_child(source=source, **child_data)
                        
                        self._log_audit('CREATE', 'child', child_code, None, child_data)
                        st.success(f"✅ Added Child: {child_code} under parent {parent_code}")
                        self._clear_cache()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving child: {e}")
            elif submitted:
                st.error("Please fill all required fields (Code, Description, and Parent)")
    def _child_crud_bak(self, source, edition_year, show_debug):
        """Child CRUD with editable table"""
        
        st.markdown("### 👶 Manage Child Items")
        
        can_edit = self._check_permission('update')
        
        # ✅ Use cached data
        parents = self._get_cached_parents(source)
        
        if not parents:
            st.warning("⚠️ No parents found. Please add parents first in the 'Parents' tab.")
            return
        
        children = self._get_cached_children(source)
        
        if show_debug:
            st.write(f"Debug: Loaded {len(children)} children from database")
        
        if children:
            st.markdown("#### Existing Children (Double-click to edit)")
            
            zones = self._get_cached_zones(source)
            valid_zones = [z for z in zones if z.get('code')]
            zone_names = [z.get('code', '') for z in valid_zones]
            
            # Build DataFrame efficiently
            data = []
            append = data.append
            for child in children:
                row = {
                    'Code': child.get('code', ''),
                    'Parent': child.get('parent_code', ''),
                    'Description': child.get('description', ''),
                    'Unit': child.get('unit', '')
                }
                rates = child.get('rates', {})
                for zone in zone_names:
                    if zone:
                        row[zone] = rates.get(zone, 0)
                append(row)
            
            if data:
                df = pd.DataFrame(data)
                
                for zone in zone_names:
                    if zone and zone in df.columns:
                        df[zone] = pd.to_numeric(df[zone], errors='coerce').fillna(0)
                
                column_config = {
                    "Code": st.column_config.TextColumn("Code", disabled=True),
                    "Parent": st.column_config.SelectboxColumn("Parent", options=[p.get('code', '') for p in parents if p.get('code')]),
                    "Description": st.column_config.TextColumn("Description", width="large"),
                    "Unit": st.column_config.SelectboxColumn("Unit", options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"])
                }
                
                for zone in zone_names:
                    if zone:
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
                    
                    if not edited_df.equals(df):
                        for idx in edited_df.index:
                            if not edited_df.loc[idx].equals(df.loc[idx]):
                                old_data = df.loc[idx].to_dict()
                                new_data = edited_df.loc[idx].to_dict()
                                
                                rates = {}
                                for zone in zone_names:
                                    if zone:
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
                        
                        self._clear_cache()
                        st.rerun()
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No valid child data to display.")
        else:
            st.info("No child items found. Use the form below to add new child items.")
        
        st.markdown("---")
        
        st.markdown("#### ➕ Add New Child Item")
        
        with st.form(f"add_child_form_{source}", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                child_code = st.text_input("Child Code", placeholder="01.1.1 or 1.01.01", key=f"child_code_{source}")
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
            
            zones = self._get_cached_zones(source)
            valid_zones = [z for z in zones if z.get('code')]
            
            if valid_zones:
                st.markdown("##### Rates by Zone")
                rate_cols = st.columns(len(valid_zones))
                rates = {}
                for i, zone in enumerate(valid_zones):
                    zone_code = zone.get('code', '')
                    zone_name = zone.get('name', zone_code)
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
                        self._clear_cache()
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
        
        st.markdown("#### Step 1: Select Chapter")
        
        chapters = self._get_cached_chapters("LGED")
        
        if not chapters:
            st.warning("⚠️ No LGED chapters found. Please add chapters first in the 'Chapters' tab.")
            return
        
        chapter_options = []
        append = chapter_options.append
        for ch in chapters:
            chapter_num = str(ch.get('chapter_number', ''))
            chapter_name = ch.get('chapter_name', '')
            if chapter_num:
                append(f"{chapter_num} - {chapter_name}")
        
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
            
            if show_debug:
                st.write(f"🔍 Querying sections for chapter: {chapter_num}")
            
            sections = self._get_cached_sections(chapter_num)
            
            if show_debug:
                st.write(f"🔍 Found {len(sections)} sections for chapter {chapter_num}")
            
            if sections:
                df_data = []
                append = df_data.append
                for s in sections:
                    append({
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
                            self._clear_cache()
                            st.rerun()
                    else:
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No valid section data to display.")
            else:
                st.info(f"No sections found for Chapter {chapter_num}. Add sections below.")
            
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
                                    self._clear_cache()
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
        
        if parts[0] != chapter_num:
            return False
        
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
        
        parents = self._get_cached_parents(source)
        
        if show_debug:
            st.write(f"Debug: Loaded {len(parents)} parents from database")
        
        if parents:
            st.markdown("#### Existing Parents (Double-click to edit)")
            
            df_data = []
            append = df_data.append
            for p in parents:
                row = {
                    'Code': p.get('code', ''),
                    'Chapter': p.get('chapter_number', ''),
                    'Description': p.get('description', '')
                }
                if source == "LGED":
                    row['Section'] = p.get('section_number', '')
                append(row)
            
            df = pd.DataFrame(df_data)
            
            if can_edit:
                chapters = self._get_cached_chapters(source)
                chapter_options = [ch.get('chapter_number', '') for ch in chapters] if chapters else []
                
                if source == "PWD":
                    column_config = {
                        "Code": st.column_config.TextColumn("Code", disabled=True),
                        "Chapter": st.column_config.SelectboxColumn("Chapter", options=chapter_options) if chapter_options else st.column_config.TextColumn("Chapter"),
                        "Description": st.column_config.TextColumn("Description", width="large")
                    }
                else:
                    section_options = [""]
                    if not df.empty and df.iloc[0]['Chapter']:
                        sections = self._get_cached_sections(str(df.iloc[0]['Chapter']))
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
                    
                    self._clear_cache()
                    st.rerun()
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        if self._check_permission('create'):
            with st.expander("➕ Add New Parent", expanded=False):
                chapters = self._get_cached_chapters(source)
                
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
                    
                    parent_section = ""
                    if source == "LGED" and parent_chapter:
                        sections = self._get_cached_sections(parent_chapter)
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
                        self._clear_cache()
                        st.rerun()
                    else:
                        st.error("Please fill all required fields (Code, Chapter, Description)")
    
    # ========== VERSION CRUD ==========
    def _version_crud(self, source, show_debug):
        """Version CRUD with audit log"""
        
        st.markdown("### 📦 Manage Versions")
        
        can_edit = self._check_permission('update')
        
        versions = self._get_cached_versions(source)
        
        if show_debug:
            st.write(f"Debug: Loaded {len(versions)} versions from database")
        
        if versions:
            st.markdown("#### Existing Versions")
            df = pd.DataFrame(versions)
            if not df.empty and 'is_active' in df.columns:
                df['is_active'] = df['is_active'].apply(lambda x: "✅ Active" if x else "📦 Archived")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
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
                        self._clear_cache()
                        st.rerun()
                    else:
                        st.error("Failed to activate version")
        
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
                            self._clear_cache()
                            st.rerun()
                        else:
                            st.warning(f"Version for {source} {edition_year} already exists!")
                    else:
                        st.error("Please fill version name and year")


# Convenience function
def render_rate_crud_forms(db):
    forms = RateCRUDForms(db)
    forms.render()