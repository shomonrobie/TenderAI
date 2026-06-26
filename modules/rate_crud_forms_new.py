# modules/rate_crud_forms.py - COMPLETE UPDATED VERSION

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import sqlite3
import re
import io
from modules.rbac import (
    rbac, can_view_rates, can_edit_rates, can_delete_rates,
    can_import_rates, render_role_badge, require_permission,
    render_protected_button, render_protected_data_editor
)


class RateCRUDForms:
    """Simple CRUD forms for Zones, Chapters, Parents, Children, and Versions"""
    
    def __init__(self, db):
        self.db = db

   
    
    def _log_audit(self, action, entity_type, entity_id, old_data=None, new_data=None):
        """Log audit trail"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            username = st.session_state.get('username', 'unknown')
            user_role = st.session_state.get('user_role', 'viewer')
            user_id = st.session_state.get('user_id', 0)
            
            cursor.execute("""
                INSERT INTO rate_audit_log (user_id, username, role, action, entity_type, entity_id, old_data, new_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, user_role, action, entity_type, entity_id, 
                  json.dumps(old_data) if old_data else None, 
                  json.dumps(new_data) if new_data else None))
            
            conn.commit()
            conn.close()
            st.toast(f"📝 Audit: {username} ({user_role}) - {action} {entity_type}: {entity_id}")
        except Exception as e:
            pass
    
    def _check_permission(self, permission):
        """Check if user has permission for rate management"""
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
            st.info(f"👤 Role: **{user_role.upper()}** | Plan: **{sub['plan_name']}** | "
                   f"✏️ Edit: {'✅' if can_edit_rates() else '❌'} | "
                   f"🗑️ Delete: {'✅' if can_delete_rates() else '❌'}")
        else:
            st.info(f"👤 Role: **{user_role.upper()}**")
        
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
            self._child_crud(source, edition_year, show_debug)
        with tab6:
            self._version_crud(source, show_debug)
    
    # ========== ZONE CRUD ==========
    def _zone_crud(self, source, show_debug=False):
        """Zone CRUD with editable table"""
        
        st.markdown("### 🗺️ Manage Zones")
        
        can_edit = self._check_permission('update')
        
        if not can_edit:
            st.info("ℹ️ You have view-only access to zones")
        
        zones = self._get_zones(source, show_debug)
        
        if zones:
            st.markdown("#### Existing Zones (Double-click to edit)")
            
            df = pd.DataFrame([{
                'Code': z['code'],
                'Name': z['name'],
                'Description': z.get('description', ''),
                'Divisions': z.get('divisions', ''),
                'Accessibility Bonus %': z.get('accessibility_bonus', 0) * 100
            } for z in zones])
            
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
                            self._update_zone(source, 
                                             edited_df.loc[idx, 'Code'],
                                             edited_df.loc[idx, 'Name'],
                                             edited_df.loc[idx, 'Description'],
                                             edited_df.loc[idx, 'Divisions'],
                                             edited_df.loc[idx, 'Accessibility Bonus %'] / 100)
                            self._log_audit('UPDATE', 'zone', edited_df.loc[idx, 'Code'], 
                                          df.loc[idx].to_dict(), edited_df.loc[idx].to_dict())
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
                        self._save_zone(source, zone_code, zone_name, zone_description, divisions, accessibility_bonus / 100)
                        self._log_audit('CREATE', 'zone', zone_code, None, {'code': zone_code, 'name': zone_name})
                        st.success(f"✅ Added Zone: {zone_code} - {zone_name}")
                        st.rerun()
                    else:
                        st.error("Please fill Zone Code and Zone Name")
    
    # ========== CHAPTER CRUD WITH EXCEL IMPORT ==========
    def _chapter_crud(self, source, show_debug):
        """Chapter CRUD with editable table and Excel import"""
        
        st.markdown("### 📚 Manage Chapters")
        
        # Add import options
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            self._download_chapter_template(source)
        with col2:
            with st.expander("📥 Import from Excel", expanded=False):
                self._import_chapters_from_excel(source)
        
        can_edit = self._check_permission('update')
        
        if source == "PWD":
            chapters_df = self.db.get_pwd_chapters()
        else:
            chapters_df = self.db.get_lged_chapters()
        
        if show_debug:
            st.write(f"Debug: Loaded {len(chapters_df)} chapters from database")
        
        if not chapters_df.empty:
            st.markdown("#### Existing Chapters (Double-click to edit)")
            
            if can_edit:
                edited_df = st.data_editor(
                    chapters_df,
                    use_container_width=True,
                    hide_index=True,
                    key="chapter_editor",
                    column_config={
                        "chapter_number": st.column_config.TextColumn("Chapter Number", disabled=True),
                        "chapter_name": st.column_config.TextColumn("Chapter Name"),
                        "description": st.column_config.TextColumn("Description", width="large")
                    }
                )
                
                if not edited_df.equals(chapters_df):
                    for idx in edited_df.index:
                        if not edited_df.loc[idx].equals(chapters_df.loc[idx]):
                            old_name = chapters_df.loc[idx, 'chapter_name']
                            new_name = edited_df.loc[idx, 'chapter_name']
                            
                            conn = self.db.get_connection()
                            cursor = conn.cursor()
                            if source == "PWD":
                                cursor.execute("UPDATE pwd_chapters SET chapter_name = ? WHERE chapter_number = ?", 
                                             (new_name, edited_df.loc[idx, 'chapter_number']))
                            else:
                                cursor.execute("UPDATE lged_chapters SET chapter_name = ? WHERE chapter_number = ?", 
                                             (new_name, edited_df.loc[idx, 'chapter_number']))
                            conn.commit()
                            conn.close()
                            
                            self._log_audit('UPDATE', 'chapter', edited_df.loc[idx, 'chapter_number'], 
                                          {'name': old_name}, {'name': new_name})
                    st.rerun()
            else:
                st.dataframe(chapters_df, use_container_width=True, hide_index=True)
        
        if self._check_permission('create'):
            with st.expander("➕ Add New Chapter", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    chapter_num = st.text_input("Chapter Number", placeholder="01 or 1", key="chapter_num")
                with col2:
                    chapter_name = st.text_input("Chapter Name", placeholder="Chapter Name", key="chapter_name")
                
                if st.button("Add Chapter", key="add_chapter"):
                    if chapter_num and chapter_name:
                        if source == "PWD":
                            self.db.add_pwd_chapter(chapter_num, chapter_name)
                        else:
                            self.db.add_lged_chapter(chapter_num, chapter_name)
                        self._log_audit('CREATE', 'chapter', chapter_num, None, {'number': chapter_num, 'name': chapter_name})
                        st.success(f"✅ Added Chapter {chapter_num}: {chapter_name}")
                        st.rerun()
                    else:
                        st.error("Please fill both fields")
    
    # ========== SECTION CRUD WITH EXCEL IMPORT (LGED ONLY) ==========
    def _section_crud(self, source, show_debug=False):
        """LGED Section CRUD with editable table and Excel import"""
        
        if source != "LGED":
            st.info("ℹ️ Sections are only applicable for LGED rate schedules")
            return
        
        st.markdown("### 📑 Manage LGED Sections")
        st.caption("Sections are sub-categories within chapters (e.g., 3.01 - Box Cutting)")
        
        # Add import options (only for LGED)
        col1, col2 = st.columns([1, 2])
        with col1:
            self._download_section_template()
        with col2:
            with st.expander("📥 Import Sections from Excel", expanded=False):
                self._import_sections_from_excel()
        
        can_edit = self._check_permission('update')
        
        if not can_edit:
            st.info("ℹ️ Sections are view-only. Contact system admin for modifications.")
        
        chapters_df = self.db.get_lged_chapters()
        
        if chapters_df.empty:
            st.warning("⚠️ No LGED chapters found. Please add chapters first in the 'Chapters' tab.")
            return
        
        chapter_options = []
        for _, row in chapters_df.iterrows():
            chapter_num = str(row['chapter_number'])
            chapter_name = row['chapter_name']
            chapter_options.append(f"{chapter_num} - {chapter_name}")
        
        selected_chapter = st.selectbox(
            "Select Chapter",
            options=chapter_options,
            key="section_chapter_select"
        )
        
        if selected_chapter:
            chapter_num = selected_chapter.split(" - ")[0]
            
            st.markdown(f"#### Sections for Chapter {chapter_num}")
            
            sections = self._get_sections_for_chapter(chapter_num, show_debug)
            
            if sections:
                df = pd.DataFrame([{
                    'Section Number': s['section_number'],
                    'Section Name': s['section_name'],
                    'Description': s.get('description', ''),
                    'Display Order': s.get('display_order', 0)
                } for s in sections])
                
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
                                self._update_section(
                                    chapter_num,
                                    edited_df.loc[idx, 'Section Number'],
                                    edited_df.loc[idx, 'Section Name'],
                                    edited_df.loc[idx, 'Description'],
                                    edited_df.loc[idx, 'Display Order']
                                )
                        st.rerun()
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
            
            if self._check_permission('create'):
                with st.expander("➕ Add New Section", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        auto_number = st.checkbox("Auto-generate", value=True, key="auto_section_num")
                        if auto_number:
                            next_section_num = self._get_next_section_number(chapter_num, sections)
                            section_number = st.text_input("Section Number", value=next_section_num, disabled=True)
                        else:
                            section_number = st.text_input("Section Number", placeholder=f"{chapter_num}.01")
                        section_name = st.text_input("Section Name", placeholder="e.g., Box Cutting")
                    with col2:
                        section_description = st.text_area("Description", height=100)
                        display_order = st.number_input("Display Order", min_value=0, max_value=999, value=0)
                    
                    if st.button("Add Section", key=f"add_section_{chapter_num}"):
                        if section_number and section_name:
                            if self._validate_lged_section_number(section_number, chapter_num):
                                self._save_section(chapter_num, section_number, section_name, section_description, display_order)
                                self._log_audit('CREATE', 'section', section_number, None, 
                                              {'chapter': chapter_num, 'section': section_number, 'name': section_name})
                                st.success(f"✅ Added Section: {section_number}")
                                st.rerun()
                            else:
                                st.error(f"Section number must be format: {chapter_num}.XX")
                        else:
                            st.error("Please fill required fields")
    
    # ========== EXCEL IMPORT FUNCTIONS ==========
    
    def _import_chapters_from_excel(self, source: str):
        """Import chapters from Excel file with validation"""
        
        st.markdown("##### Upload Excel File")
        st.caption("Format: Chapter Number, Chapter Name, Description (optional)")
        
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=["xlsx", "xls"],
            key=f"import_chapters_{source}"
        )
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                
                st.markdown("**Preview:**")
                st.dataframe(df.head(5), use_container_width=True)
                
                # Normalize column names
                df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
                
                # Find required columns
                number_col = None
                name_col = None
                for col in df.columns:
                    if 'number' in col or 'chapter_no' in col:
                        number_col = col
                    if 'name' in col or 'chapter_name' in col:
                        name_col = col
                
                if not number_col or not name_col:
                    st.error("❌ Excel must have Chapter Number and Chapter Name columns")
                    return
                
                # Get existing chapters
                existing = set()
                conn = self.db.get_connection()
                cursor = conn.cursor()
                if source == "PWD":
                    cursor.execute("SELECT chapter_number FROM pwd_chapters")
                else:
                    cursor.execute("SELECT chapter_number FROM lged_chapters")
                existing = {str(row[0]) for row in cursor.fetchall()}
                conn.close()
                
                # Validate and prepare data
                valid_data = []
                errors = []
                
                for idx, row in df.iterrows():
                    row_num = idx + 2
                    chapter_num = str(row[number_col]).strip() if pd.notna(row[number_col]) else ""
                    chapter_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                    
                    if not chapter_num or not chapter_name or chapter_name == 'nan':
                        errors.append(f"Row {row_num}: Missing chapter number or name")
                        continue
                    
                    # Extract numeric part
                    num_match = re.search(r'\d+', chapter_num)
                    if num_match:
                        chapter_num_clean = num_match.group()
                        if source == "PWD" and len(chapter_num_clean) == 1:
                            chapter_num_clean = chapter_num_clean.zfill(2)
                    else:
                        errors.append(f"Row {row_num}: Invalid chapter number '{chapter_num}'")
                        continue
                    
                    valid_data.append({
                        'number': chapter_num_clean,
                        'name': chapter_name[:200],
                        'is_update': chapter_num_clean in existing
                    })
                
                if errors:
                    st.error(f"❌ Found {len(errors)} errors")
                    for err in errors[:10]:
                        st.write(f"- {err}")
                
                if valid_data:
                    updates = [d for d in valid_data if d['is_update']]
                    inserts = [d for d in valid_data if not d['is_update']]
                    st.info(f"📋 {len(inserts)} new chapters, {len(updates)} updates")
                    
                    if st.button(f"✅ Import {len(valid_data)} Chapters", key=f"confirm_import_{source}"):
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        success = 0
                        for data in valid_data:
                            try:
                                if source == "PWD":
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO pwd_chapters (chapter_number, chapter_name)
                                        VALUES (?, ?)
                                    """, (data['number'], data['name']))
                                else:
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO lged_chapters (chapter_number, chapter_name)
                                        VALUES (?, ?)
                                    """, (data['number'], data['name']))
                                success += 1
                            except Exception as e:
                                errors.append(f"{data['number']}: {e}")
                        
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Imported {success} chapters")
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    def _import_sections_from_excel(self):
        """Import LGED sections from Excel file with validation"""
        
        st.markdown("##### Upload Excel File")
        st.caption("Format: Chapter Number, Section Number, Section Name, Description (optional)")
        
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=["xlsx", "xls"],
            key="import_sections"
        )
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                
                st.markdown("**Preview:**")
                st.dataframe(df.head(5), use_container_width=True)
                
                df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
                
                # Find required columns
                chapter_col = None
                section_num_col = None
                section_name_col = None
                
                for col in df.columns:
                    if 'chapter' in col:
                        chapter_col = col
                    if 'section_number' in col or 'section_no' in col:
                        section_num_col = col
                    if 'section_name' in col or ('section' in col and 'number' not in col):
                        section_name_col = col
                
                if not chapter_col or not section_num_col or not section_name_col:
                    st.error("❌ Excel must have Chapter Number, Section Number, and Section Name columns")
                    return
                
                # Get existing chapters for validation
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT chapter_number FROM lged_chapters")
                existing_chapters = {str(row[0]) for row in cursor.fetchall()}
                conn.close()
                
                # Validate
                valid_data = []
                errors = []
                
                for idx, row in df.iterrows():
                    row_num = idx + 2
                    chapter = str(row[chapter_col]).strip() if pd.notna(row[chapter_col]) else ""
                    section_num = str(row[section_num_col]).strip() if pd.notna(row[section_num_col]) else ""
                    section_name = str(row[section_name_col]).strip() if pd.notna(row[section_name_col]) else ""
                    
                    if not chapter or not section_num or not section_name or section_name == 'nan':
                        errors.append(f"Row {row_num}: Missing required fields")
                        continue
                    
                    # Extract numeric chapter
                    chapter_match = re.search(r'\d+', chapter)
                    if not chapter_match:
                        errors.append(f"Row {row_num}: Invalid chapter number")
                        continue
                    chapter_clean = chapter_match.group()
                    
                    if chapter_clean not in existing_chapters:
                        errors.append(f"Row {row_num}: Chapter {chapter_clean} does not exist")
                        continue
                    
                    # Validate section number format
                    section_match = re.match(r'^(\d+)\.(\d{1,2})$', section_num)
                    if not section_match:
                        errors.append(f"Row {row_num}: Invalid section number format (use X.YY)")
                        continue
                    
                    if section_match.group(1) != chapter_clean:
                        errors.append(f"Row {row_num}: Section number chapter ({section_match.group(1)}) doesn't match chapter column ({chapter_clean})")
                        continue
                    
                    # Format section number with two digits
                    section_formatted = f"{chapter_clean}.{int(section_match.group(2)):02d}"
                    
                    valid_data.append({
                        'chapter': chapter_clean,
                        'section_number': section_formatted,
                        'section_name': section_name[:200],
                        'description': str(row.get('description', '')).strip() if 'description' in df.columns else ''
                    })
                
                if errors:
                    st.error(f"❌ Found {len(errors)} errors")
                    for err in errors[:10]:
                        st.write(f"- {err}")
                
                if valid_data:
                    st.info(f"📋 Ready to import {len(valid_data)} sections")
                    
                    if st.button(f"✅ Import {len(valid_data)} Sections", key="confirm_import_sections"):
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        success = 0
                        for data in valid_data:
                            try:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO lged_sections 
                                    (chapter_number, section_number, section_name, description, display_order)
                                    VALUES (?, ?, ?, ?, 0)
                                """, (data['chapter'], data['section_number'], data['section_name'], data['description']))
                                success += 1
                            except Exception as e:
                                errors.append(f"{data['section_number']}: {e}")
                        
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Imported {success} sections")
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    # ========== TEMPLATE DOWNLOADS ==========
    
    def _download_chapter_template(self, source: str):
        """Download Excel template for chapters"""
        
        if source == "PWD":
            template_data = {
                'chapter_number': ['01', '02', '03', '04', '05'],
                'chapter_name': ['General Works', 'Earth Works', 'Concrete Works', 'Reinforcement', 'Finishing'],
                'description': ['General construction works', 'Excavation and filling', 'RCC and PCC works', 'Steel reinforcement', 'Plaster and painting']
            }
        else:
            template_data = {
                'chapter_number': ['1', '2', '3', '4', '5'],
                'chapter_name': ['General Works', 'Earth Works', 'Sub-Base', 'Base Course', 'Pavement'],
                'description': ['General guidelines', 'Earth excavation', 'Sub-base layer', 'Base course', 'Bituminous pavement']
            }
        
        df = pd.DataFrame(template_data)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Chapters', index=False)
            instructions = pd.DataFrame({
                'Instruction': [
                    '1. First row must contain headers: chapter_number, chapter_name, description',
                    f'2. For PWD use two-digit format (01, 02). For LGED use single-digit (1, 2)',
                    '3. Chapter name cannot be empty',
                    '4. Description is optional',
                    '5. Existing chapters will be updated if chapter_number exists'
                ]
            })
            instructions.to_excel(writer, sheet_name='Instructions', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Download Template",
            data=output,
            file_name=f"{source.lower()}_chapters_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_template_{source}"
        )
    
    def _download_section_template(self):
        """Download Excel template for LGED sections"""
        
        template_data = {
            'chapter_number': ['1', '1', '1', '2', '2'],
            'section_number': ['1.01', '1.02', '1.03', '2.01', '2.02'],
            'section_name': ['Site Office Setup', 'Videography Services', 'Safety Equipment', 'Earth Excavation', 'Earth Filling'],
            'description': ['Setting up site office', 'Video documentation', 'Safety gear', 'Excavation work', 'Earth filling and compaction']
        }
        
        df = pd.DataFrame(template_data)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sections', index=False)
            instructions = pd.DataFrame({
                'Instruction': [
                    '1. Headers: chapter_number, section_number, section_name, description',
                    '2. chapter_number must match existing LGED chapters',
                    '3. section_number format: X.YY (e.g., 1.01)',
                    '4. Section name cannot be empty',
                    '5. Sections are ONLY for LGED (PWD does not have sections)'
                ]
            })
            instructions.to_excel(writer, sheet_name='Instructions', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Download LGED Section Template",
            data=output,
            file_name="lged_sections_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_section_template"
        )
    
    # ========== VERSION CRUD ==========
    def _version_crud(self, source, show_debug):
        """Version CRUD with audit log and version management"""
        
        st.markdown("### 📦 Manage Versions")
        
        can_edit = self._check_permission('update')
        
        conn = self.db.get_connection()
        versions_df = pd.read_sql_query("""
            SELECT id, version_name, edition_year, effective_from, is_active, 
                   release_date, created_by, total_parents, total_children, total_rates
            FROM rate_versions 
            WHERE source = ?
            ORDER BY edition_year DESC
        """, conn, params=(source,))
        conn.close()
        
        if show_debug:
            st.write(f"Debug: Loaded {len(versions_df)} versions from database")
        
        if not versions_df.empty:
            st.markdown("#### Existing Versions")
            display_df = versions_df.copy()
            display_df['is_active'] = display_df['is_active'].apply(lambda x: "✅ Active" if x else "📦 Archived")
            display_df['total_items'] = display_df['total_parents'] + display_df['total_children']
            st.dataframe(display_df[['id', 'version_name', 'edition_year', 'effective_from', 'is_active', 'total_items']], 
                        use_container_width=True, hide_index=True)
            
            if can_edit:
                st.markdown("---")
                st.markdown("#### Set Active Version")
                version_to_activate = st.selectbox(
                    "Select Version to Activate",
                    options=versions_df['id'].tolist(),
                    format_func=lambda x: f"{versions_df[versions_df['id']==x]['version_name'].iloc[0]} ({versions_df[versions_df['id']==x]['edition_year'].iloc[0]})",
                    key="activate_version"
                )
                if st.button("Set as Active", key="confirm_activate"):
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE rate_versions SET is_active = 0 WHERE source = ?", (source,))
                    cursor.execute("UPDATE rate_versions SET is_active = 1 WHERE id = ?", (version_to_activate,))
                    conn.commit()
                    conn.close()
                    
                    self._log_audit('ACTIVATE', 'version', str(version_to_activate), None, {'version_id': version_to_activate})
                    st.success("✅ Version activated!")
                    st.rerun()
        
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
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM rate_versions WHERE source = ? AND edition_year = ?", (source, edition_year))
                        existing = cursor.fetchone()
                        
                        if existing:
                            st.warning(f"Version for {source} {edition_year} already exists!")
                        else:
                            if is_active:
                                cursor.execute("UPDATE rate_versions SET is_active = 0 WHERE source = ?", (source,))
                            
                            cursor.execute("""
                                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, 
                                                          release_date, created_by, total_parents, total_children, total_rates)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
                            """, (source, version_name, edition_year, effective_date, 1 if is_active else 0, 
                                  datetime.now(), st.session_state.get('username', 'admin')))
                            
                            conn.commit()
                            self._log_audit('CREATE', 'version', version_name, None, 
                                          {'name': version_name, 'year': edition_year, 'active': is_active})
                            st.success(f"✅ Added Version: {version_name} ({edition_year})")
                            st.rerun()
                        
                        conn.close()
                    else:
                        st.error("Please fill version name and year")
    
    # ========== HELPER METHODS ==========
    
    def _get_zones(self, source, show_debug=False):
        """Get zones from database"""
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
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        SELECT zone_code, zone_name, divisions, accessibility_bonus, description 
                        FROM lged_zone_mapping ORDER BY zone_code
                    """)
                    zones = [{'code': r[0], 'name': r[1], 'divisions': r[2], 
                            'accessibility_bonus': r[3], 'description': r[4] if len(r) > 4 else ''} 
                            for r in cursor.fetchall()]
                except sqlite3.OperationalError:
                    cursor.execute("""
                        SELECT zone_code, zone_name, divisions, accessibility_bonus 
                        FROM lged_zone_mapping ORDER BY zone_code
                    """)
                    zones = [{'code': r[0], 'name': r[1], 'divisions': r[2], 
                            'accessibility_bonus': r[3], 'description': ''} 
                            for r in cursor.fetchall()]
            conn.close()
            return zones
        except Exception as e:
            if show_debug:
                st.error(f"Zone load error: {e}")
            return []
    
    def _get_parents(self, source):
        """Get parent items from database"""
        try:
            conn = self.db.get_connection()
            if source == "PWD":
                query = "SELECT pwd_code as code, description, chapter_number FROM pwd_parents ORDER BY pwd_code"
            else:
                query = "SELECT code, description, chapter_number, section_number FROM lged_parents ORDER BY code"
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.to_dict('records')
        except Exception as e:
            print(f"Error getting parents: {e}")
            return []
    
    def _get_children(self, source):
        """Get children with their rates from database"""
        try:
            conn = self.db.get_connection()
            children = []
            
            if source == "PWD":
                children_df = pd.read_sql_query("""
                    SELECT c.pwd_code as code, c.parent_code, c.description, c.unit, 
                           r.zone_name, r.unit_rate
                    FROM pwd_children c
                    LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                    ORDER BY c.pwd_code
                """, conn)
                
                child_dict = {}
                for _, row in children_df.iterrows():
                    code = row['code']
                    if code not in child_dict:
                        child_dict[code] = {
                            'code': code,
                            'parent_code': row['parent_code'],
                            'description': row['description'],
                            'unit': row['unit'],
                            'rates': {}
                        }
                    if row['zone_name']:
                        child_dict[code]['rates'][row['zone_name']] = row['unit_rate']
                children = list(child_dict.values())
            else:
                children_df = pd.read_sql_query("""
                    SELECT c.code, c.parent_code, c.description, c.unit, r.zone_name, r.unit_rate
                    FROM lged_children c
                    LEFT JOIN lged_zone_rates r ON c.id = r.child_id
                    ORDER BY c.code
                """, conn)
                
                child_dict = {}
                for _, row in children_df.iterrows():
                    code = row['code']
                    if code not in child_dict:
                        child_dict[code] = {
                            'code': code,
                            'parent_code': row['parent_code'],
                            'description': row['description'],
                            'unit': row['unit'],
                            'rates': {}
                        }
                    if row['zone_name']:
                        child_dict[code]['rates'][row['zone_name']] = row['unit_rate']
                children = list(child_dict.values())
            
            conn.close()
            return children
        except Exception as e:
            return []
    
    def _save_zone(self, source, code, name, description, divisions, bonus):
        """Save zone to database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if source == "PWD":
                st.info("PWD zones are predefined. Use LGED for custom zones.")
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO lged_zone_mapping (zone_code, zone_name, divisions, accessibility_bonus, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (code, name, divisions, bonus, description))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error saving zone: {e}")
    
    def _update_zone(self, source, code, name, description, divisions, bonus):
        """Update zone"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if source == "LGED":
                cursor.execute("""
                    UPDATE lged_zone_mapping 
                    SET zone_name = ?, divisions = ?, accessibility_bonus = ?, description = ?
                    WHERE zone_code = ?
                """, (name, divisions, bonus, description, code))
                conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error updating zone: {e}")
    
    def _parent_crud(self, source, edition_year, show_debug):
        """Parent CRUD with editable table"""
        
        st.markdown("### 📁 Manage Parents")
        
        can_edit = self._check_permission('update')
        
        existing_parents = self._get_parents(source)
        
        if show_debug:
            st.write(f"Debug: Loaded {len(existing_parents)} parents from database")
        
        if existing_parents:
            st.markdown("#### Existing Parents (Double-click to edit)")
            
            df_data = []
            for p in existing_parents:
                row = {'Code': p['code'], 'Chapter': p.get('chapter_number', ''), 'Description': p['description']}
                if source == "LGED":
                    row['Section'] = p.get('section_number', '')
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            if can_edit:
                if source == "PWD":
                    chapters_df = self.db.get_pwd_chapters()
                    chapter_options = chapters_df['chapter_number'].tolist() if not chapters_df.empty else []
                    column_config = {
                        "Code": st.column_config.TextColumn("Code", disabled=True),
                        "Chapter": st.column_config.SelectboxColumn("Chapter", options=chapter_options),
                        "Description": st.column_config.TextColumn("Description", width="large")
                    }
                else:
                    chapters_df = self.db.get_lged_chapters()
                    chapter_options = chapters_df['chapter_number'].tolist() if not chapters_df.empty else []
                    section_options = [""]
                    if not df.empty and df.iloc[0]['Chapter']:
                        sections_df = self._get_lged_sections_for_chapter(str(df.iloc[0]['Chapter']))
                        section_options = [""] + sections_df['section_number'].tolist() if not sections_df.empty else [""]
                    
                    column_config = {
                        "Code": st.column_config.TextColumn("Code", disabled=True),
                        "Chapter": st.column_config.SelectboxColumn("Chapter", options=chapter_options),
                        "Section": st.column_config.SelectboxColumn("Section", options=section_options),
                        "Description": st.column_config.TextColumn("Description", width="large")
                    }
                
                edited_df = st.data_editor(df, use_container_width=True, hide_index=True, key="parent_editor", column_config=column_config)
                
                if not edited_df.equals(df):
                    for idx in edited_df.index:
                        if not edited_df.loc[idx].equals(df.loc[idx]):
                            conn = self.db.get_connection()
                            cursor = conn.cursor()
                            
                            if source == "PWD":
                                cursor.execute("""
                                    UPDATE pwd_parents SET chapter_number = ?, description = ?
                                    WHERE pwd_code = ?
                                """, (edited_df.loc[idx, 'Chapter'], edited_df.loc[idx, 'Description'], edited_df.loc[idx, 'Code']))
                            else:
                                section_value = edited_df.loc[idx].get('Section', '') if 'Section' in edited_df.columns else ''
                                cursor.execute("""
                                    UPDATE lged_parents SET chapter_number = ?, section_number = ?, description = ?
                                    WHERE code = ?
                                """, (edited_df.loc[idx, 'Chapter'], section_value, edited_df.loc[idx, 'Description'], edited_df.loc[idx, 'Code']))
                            
                            conn.commit()
                            conn.close()
                            self._log_audit('UPDATE', 'parent', edited_df.loc[idx, 'Code'], df.loc[idx].to_dict(), edited_df.loc[idx].to_dict())
                    st.rerun()
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        if self._check_permission('create'):
            with st.expander("➕ Add New Parent", expanded=False):
                if source == "PWD":
                    chapters_df = self.db.get_pwd_chapters()
                else:
                    chapters_df = self.db.get_lged_chapters()
                
                chapter_options = ["-- Select Chapter --"]
                chapter_map = {}
                for _, row in chapters_df.iterrows():
                    display_text = f"{row['chapter_number']} - {row['chapter_name']}"
                    chapter_options.append(display_text)
                    chapter_map[display_text] = row['chapter_number']
                
                col1, col2 = st.columns(2)
                with col1:
                    parent_code = st.text_input("Parent Code", placeholder="01.1 or 1.01", key="parent_code")
                    selected_chapter = st.selectbox("Chapter", chapter_options, key="parent_chapter")
                    parent_chapter = chapter_map[selected_chapter] if selected_chapter != "-- Select Chapter --" else ""
                    
                    parent_section = ""
                    if source == "LGED" and parent_chapter:
                        sections_df = self._get_lged_sections_for_chapter(parent_chapter)
                        if not sections_df.empty:
                            section_options = ["-- No Section --"] + sections_df['section_number'].tolist()
                            selected_section = st.selectbox("Section (Optional)", section_options, key="parent_section")
                            if selected_section != "-- No Section --":
                                parent_section = selected_section
                
                with col2:
                    parent_desc = st.text_area("Parent Description", placeholder="Full description", height=100, key="parent_desc")
                
                if st.button("Add Parent", key="add_parent"):
                    if parent_code and parent_desc and parent_chapter:
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        
                        if source == "PWD":
                            cursor.execute("""
                                INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number)
                                VALUES (?, ?, ?)
                            """, (parent_code, parent_desc, parent_chapter))
                        else:
                            cursor.execute("PRAGMA table_info(lged_parents)")
                            columns = [col[1] for col in cursor.fetchall()]
                            
                            if 'section_number' in columns:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO lged_parents (code, description, chapter_number, section_number)
                                    VALUES (?, ?, ?, ?)
                                """, (parent_code, parent_desc, parent_chapter, parent_section))
                            else:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO lged_parents (code, description, chapter_number)
                                    VALUES (?, ?, ?)
                                """, (parent_code, parent_desc, parent_chapter))
                        
                        conn.commit()
                        conn.close()
                        self._log_audit('CREATE', 'parent', parent_code, None, {'code': parent_code, 'chapter': parent_chapter})
                        st.success(f"✅ Added Parent: {parent_code}")
                        st.rerun()
                    else:
                        st.error("Please fill all required fields")
    
    def _child_crud(self, source, edition_year, show_debug):
        """Child CRUD with editable table"""
        
        st.markdown("### 👶 Manage Child Items")
        
        can_edit = self._check_permission('update')
        
        existing_parents = self._get_parents(source)
        
        if not existing_parents:
            st.warning("⚠️ No parents found. Please add parents first.")
            return
        
        existing_children = self._get_children(source)
        
        if show_debug:
            st.write(f"Debug: Loaded {len(existing_children)} children from database")
        
        if existing_children:
            st.markdown("#### Existing Children (Double-click to edit)")
            
            zones = self._get_zones(source)
            zone_names = [z['code'] for z in zones]
            
            data = []
            for child in existing_children:
                row = {'Code': child['code'], 'Parent': child['parent_code'], 
                       'Description': child['description'], 'Unit': child.get('unit', '')}
                for zone in zone_names:
                    row[zone] = child.get('rates', {}).get(zone, 0)
                data.append(row)
            
            df = pd.DataFrame(data)
            for zone in zone_names:
                if zone in df.columns:
                    df[zone] = pd.to_numeric(df[zone], errors='coerce').fillna(0)
            
            column_config = {
                "Code": st.column_config.TextColumn("Code", disabled=True),
                "Parent": st.column_config.SelectboxColumn("Parent", options=[p['code'] for p in existing_parents]),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Unit": st.column_config.SelectboxColumn("Unit", options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"])
            }
            for zone in zone_names:
                column_config[zone] = st.column_config.NumberColumn(f"{zone}", format="%.2f", step=100.0)
            
            if can_edit:
                edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True, key="child_editor")
                
                if not edited_df.equals(df):
                    for idx in edited_df.index:
                        if not edited_df.loc[idx].equals(df.loc[idx]):
                            conn = self.db.get_connection()
                            cursor = conn.cursor()
                            
                            if source == "PWD":
                                cursor.execute("""
                                    UPDATE pwd_children SET parent_code = ?, description = ?, unit = ?
                                    WHERE pwd_code = ?
                                """, (edited_df.loc[idx, 'Parent'], edited_df.loc[idx, 'Description'], 
                                    edited_df.loc[idx, 'Unit'], edited_df.loc[idx, 'Code']))
                                
                                for zone in zone_names:
                                    rate = edited_df.loc[idx, zone]
                                    if rate and rate > 0:
                                        cursor.execute("""
                                            INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year)
                                            VALUES (?, ?, ?, ?)
                                        """, (edited_df.loc[idx, 'Code'], zone, float(rate), edition_year))
                                    else:
                                        cursor.execute("DELETE FROM pwd_rates WHERE pwd_code = ? AND zone_name = ?", 
                                                    (edited_df.loc[idx, 'Code'], zone))
                            else:
                                cursor.execute("""
                                    UPDATE lged_children SET parent_code = ?, description = ?, unit = ?
                                    WHERE code = ?
                                """, (edited_df.loc[idx, 'Parent'], edited_df.loc[idx, 'Description'], 
                                    edited_df.loc[idx, 'Unit'], edited_df.loc[idx, 'Code']))
                                
                                cursor.execute("SELECT id FROM lged_children WHERE code = ?", (edited_df.loc[idx, 'Code'],))
                                child_id = cursor.fetchone()[0]
                                
                                for zone in zone_names:
                                    rate = edited_df.loc[idx, zone]
                                    if rate and rate > 0:
                                        cursor.execute("""
                                            INSERT OR REPLACE INTO lged_zone_rates (child_id, zone_name, unit_rate)
                                            VALUES (?, ?, ?)
                                        """, (child_id, zone, float(rate)))
                                    else:
                                        cursor.execute("DELETE FROM lged_zone_rates WHERE child_id = ? AND zone_name = ?", 
                                                    (child_id, zone))
                            
                            conn.commit()
                            conn.close()
                            self._log_audit('UPDATE', 'child', edited_df.loc[idx, 'Code'], df.loc[idx].to_dict(), edited_df.loc[idx].to_dict())
                    st.rerun()
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No child items found. Use the form below to add new child items.")
        
        st.markdown("---")
        st.markdown("#### ➕ Add New Child Item")
        
        with st.form("add_child_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                child_code = st.text_input("Child Code", placeholder="01.1.1 or 1.01.01", key="child_code")
                parent_options = ["-- Select Parent --"] + [f"{p['code']} - {p['description'][:50]}..." for p in existing_parents]
                selected_parent = st.selectbox("Select Parent", parent_options, key="child_parent")
                
                if selected_parent != "-- Select Parent --":
                    parent_code = selected_parent.split(" - ")[0]
                    if child_code and not child_code.startswith(parent_code):
                        st.warning(f"⚠️ Child code should start with '{parent_code}'")
                else:
                    parent_code = ""
                unit = st.selectbox("Unit", ["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], key="child_unit")
            
            with col2:
                child_desc = st.text_area("Description", placeholder="Item description", height=100, key="child_desc")
            
            zones = self._get_zones(source)
            st.markdown("##### Rates by Zone")
            rate_cols = st.columns(len(zones))
            rates = {}
            for i, zone in enumerate(zones):
                with rate_cols[i]:
                    rates[zone['code']] = st.number_input(f"{zone['name']}", value=0.0, step=100.0, format="%.2f", key=f"new_child_rate_{zone['code']}")
            
            submitted = st.form_submit_button("➕ Add Child Item", use_container_width=True)
            
            if submitted and child_code and child_desc and parent_code:
                if not child_code.startswith(parent_code):
                    st.error(f"Child code must start with parent code '{parent_code}'")
                else:
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    
                    if source == "PWD":
                        cursor.execute("""
                            INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year)
                            VALUES (?, ?, ?, ?, ?)
                        """, (child_code, parent_code, child_desc, unit, edition_year))
                        for zone, rate in rates.items():
                            if rate > 0:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year)
                                    VALUES (?, ?, ?, ?)
                                """, (child_code, zone, rate, edition_year))
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO lged_children (code, parent_code, description, unit, edition_year)
                            VALUES (?, ?, ?, ?, ?)
                        """, (child_code, parent_code, child_desc, unit, edition_year))
                        cursor.execute("SELECT id FROM lged_children WHERE code = ?", (child_code,))
                        child_id = cursor.fetchone()[0]
                        for zone, rate in rates.items():
                            if rate > 0:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO lged_zone_rates (child_id, zone_name, unit_rate)
                                    VALUES (?, ?, ?)
                                """, (child_id, zone, rate))
                    
                    conn.commit()
                    conn.close()
                    self._log_audit('CREATE', 'child', child_code, None, {'code': child_code, 'parent': parent_code})
                    st.success(f"✅ Added Child: {child_code} under parent {parent_code}")
                    st.rerun()
            elif submitted:
                st.error("Please fill all required fields")
    
    def _get_lged_sections_for_chapter(self, chapter_num: str) -> pd.DataFrame:
        """Get sections for a specific LGED chapter"""
        try:
            conn = self.db.get_connection()
            df = pd.read_sql_query("""
                SELECT section_number, section_name, display_order
                FROM lged_sections WHERE chapter_number = ?
                ORDER BY display_order, section_number
            """, conn, params=[chapter_num])
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame()
    
    def _get_sections_for_chapter(self, chapter_num: str, show_debug=False) -> list:
        """Get sections from lged_sections table"""
        try:
            conn = self.db.get_connection()
            df = pd.read_sql_query("""
                SELECT id, section_number, section_name, description, display_order
                FROM lged_sections WHERE chapter_number = ?
                ORDER BY display_order, section_number
            """, conn, params=[chapter_num])
            conn.close()
            return df.to_dict('records')
        except Exception as e:
            if show_debug:
                st.error(f"Error getting sections: {e}")
            return []
    
    def _save_section(self, chapter_num, section_number, section_name, description, display_order):
        """Save section to database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO lged_sections (chapter_number, section_number, section_name, description, display_order)
                VALUES (?, ?, ?, ?, ?)
            """, (chapter_num, section_number, section_name, description, display_order))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error saving section: {e}")
            return False
    
    def _update_section(self, chapter_num, section_number, section_name, description, display_order):
        """Update section"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE lged_sections SET section_name = ?, description = ?, display_order = ?
                WHERE chapter_number = ? AND section_number = ?
            """, (section_name, description, display_order, chapter_num, section_number))
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error updating section: {e}")
    
    def _validate_lged_section_number(self, section_number: str, chapter_num: str) -> bool:
        """Validate LGED section number format"""
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
    
    def _get_next_section_number(self, chapter_num: str, existing_sections: list = None) -> str:
        """Generate next available section number"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT section_number FROM lged_sections WHERE chapter_number = ?
                ORDER BY CAST(SUBSTR(section_number, INSTR(section_number, '.') + 1) AS INTEGER) DESC LIMIT 1
            """, (chapter_num,))
            result = cursor.fetchone()
            conn.close()
            if result:
                last_section = result[0]
                if '.' in last_section:
                    last_num = int(last_section.split('.')[1])
                    next_num = last_num + 1
                    if next_num > 99:
                        next_num = 99
                    return f"{chapter_num}.{next_num:02d}"
            return f"{chapter_num}.01"
        except Exception as e:
            return f"{chapter_num}.01"


def render_rate_crud_forms(db):
    forms = RateCRUDForms(db)
    forms.render()